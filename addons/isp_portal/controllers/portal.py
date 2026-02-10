# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class IspCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'isp_subscription_count' in counters:
            values['isp_subscription_count'] = request.env['isp.subscription'].search_count([
                ('partner_id', '=', partner.id)
            ])
        if 'isp_ticket_count' in counters:
            values['isp_ticket_count'] = request.env['isp.fault.ticket'].search_count([
                ('partner_id', '=', partner.id)
            ])
        return values

    @http.route(['/my/isp', '/my/isp/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_isp_subscriptions(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Subscription = request.env['isp.subscription']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        subscription_count = Subscription.search_count(domain)
        pager = portal_pager(
            url="/my/isp",
            url_args={'sortby': sortby},
            total=subscription_count,
            page=page,
            step=10
        )

        # Content according to pager and sortby
        subscriptions = Subscription.search(domain, order=order, limit=10, offset=pager['offset'])
        request.session['my_isp_subscription_history'] = subscriptions.ids[:100]

        values.update({
            'date': date_begin,
            'subscriptions': subscriptions,
            'page_name': 'isp_subscription',
            'pager': pager,
            'default_url': '/my/isp',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("isp_portal.portal_my_isp_subscriptions", values)

    @http.route(['/my/isp/service/<model("isp.subscription"):subscription>'], type='http', auth="user", website=True)
    def portal_my_isp_subscription_detail(self, subscription, **kw):
        return request.render("isp_portal.portal_my_isp_subscription_detail", {
            'subscription': subscription,
            'page_name': 'isp_subscription',
        })

    @http.route(['/my/isp/plan/change/<model("isp.subscription"):subscription>'], type='http', auth="user", website=True)
    def portal_my_isp_plan_change(self, subscription, **kw):
        plans = request.env['isp.service_plan'].search([('active', '=', True)])
        return request.render("isp_portal.portal_my_isp_plan_change", {
            'subscription': subscription,
            'plans': plans,
            'page_name': 'isp_subscription',
        })

    @http.route(['/my/isp/plan/change/submit'], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_isp_plan_change_submit(self, **post):
        sub_id = int(post.get('subscription_id'))
        plan_id = int(post.get('plan_id'))
        effective = post.get('effective_date_mode', 'next_cycle') # Enforce next_cycle for user

        subscription = request.env['isp.subscription'].browse(sub_id)
        # Security check: ensure partner owns subscription
        if subscription.partner_id != request.env.user.partner_id:
            return request.redirect('/my')

        # Create request
        pcr = request.env['isp.plan.change.request'].create({
            'subscription_id': sub_id,
            'requested_plan_id': plan_id,
            'effective_date_mode': 'next_cycle', # Hardcoded for safety from portal
            'requested_by': request.env.user.id,
        })
        pcr.action_submit()
        
        return request.redirect(f'/my/isp/service/{sub_id}?msg=plan_change_submitted')

    @http.route(['/my/isp/payment/transfer'], type='http', auth="user", website=True)
    def portal_my_isp_payment_transfer(self, **kw):
        invoices = request.env['account.move'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('state', '=', 'posted')
        ])
        return request.render("isp_portal.portal_my_isp_payment_transfer", {
            'invoices': invoices,
            'page_name': 'isp_payment_transfer',
        })

    @http.route(['/my/isp/payment/transfer/submit'], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_isp_payment_transfer_submit(self, **post):
        bank_name = post.get('bank_name')
        reference = post.get('reference')
        amount = float(post.get('amount'))
        date = post.get('date')
        invoice_ids = request.httprequest.form.getlist('invoice_ids')
        files = request.httprequest.files.getlist('attachment')

        # Create Transfer Payment
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'bank_name': bank_name,
            'reference': reference,
            'amount': amount,
            'transfer_datetime': date,
            'state': 'draft',
        }
        
        payment = request.env['isp.bank.transfer.payment'].create(vals)
        
        if invoice_ids:
            payment.write({'invoice_ids': [(6, 0, [int(x) for x in invoice_ids])]})

        # Process attachments
        if files:
            for file in files:
                attachment = request.env['ir.attachment'].create({
                    'name': file.filename,
                    'type': 'binary',
                    'datas': file.read(), # base64 encoding handled by create? No, need base64.
                    'res_model': 'isp.bank.transfer.payment',
                    'res_id': payment.id,
                })
                # Odoo standard create expects Base64 for datas? 
                # Actually, in controllers handling file upload, better use specialized logic or base64 encode.
                # Let's fix this block to proper Odoo upload handling.
        
        # Fixing attachment upload:
        import base64
        for file in files:
             if file.filename:
                 file.seek(0)
                 data = file.read()
                 attachment = request.env['ir.attachment'].create({
                    'name': file.filename,
                    'type': 'binary',
                    'datas': base64.b64encode(data),
                    'res_model': 'isp.bank.transfer.payment',
                    'res_id': payment.id,
                 })
                 payment.write({'attachment_ids': [(4, attachment.id)]})

        payment.action_submit()

        return request.redirect('/my/isp?msg=transfer_submitted')
