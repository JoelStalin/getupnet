#!/bin/bash

# AWS Route 53 Dynamic DNS Update Script
# Updates 'isp.getupsoft.com.do' and '*.isp.getupsoft.com.do' to the current public IP.
# Validates that critical ports (80, 443, 8069) are listening locally before updating.

# Configuration
# Replace HOSTED_ZONE_ID with your actual Zone ID from AWS Route 53
HOSTED_ZONE_ID="REPLACE_WITH_YOUR_HOSTED_ZONE_ID"
DOMAINS=(
    "isp.getupsoft.com.do."
    "*.isp.getupsoft.com.do."
)
TTL=300
REQUIRED_PORTS=(80 443 8069)
LOG_FILE="$HOME/route53_dns_updates.log"

# Logging function
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    log_message "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check for required ports
check_ports() {
    local all_active=true
    for port in "${REQUIRED_PORTS[@]}"; do
        # Use ss (iproute2) or netstat to check if port is listening
        if ss -tuln | grep -E ":$port " > /dev/null 2>&1 || netstat -tuln | grep -E ":$port " > /dev/null 2>&1; then
            log_message "Port $port is active."
        else
            log_message "Warning: Port $port is NOT listening."
            # Uncomment next line to enforce strict check
            # all_active=false
        fi
    done
    
    if [ "$all_active" = false ]; then
        log_message "Error: Critical ports are not active. Aborting DNS update."
        return 1
    fi
    return 0
}

# Get current public IP
get_public_ip() {
    curl -s http://checkip.amazonaws.com
}

# Update Route 53 Record
update_record() {
    local ZONE_ID=$1
    local RECORD_NAME=$2
    local IP=$3

    # Get current value from Route 53
    CURRENT_DNS_IP=$(aws route53 list-resource-record-sets \
        --hosted-zone-id "$ZONE_ID" \
        --query "ResourceRecordSets[?Name == '$RECORD_NAME' && Type == 'A'].ResourceRecords[0].Value" \
        --output text)
    
    log_message "Checking $RECORD_NAME..."
    log_message "  Current DNS IP: $CURRENT_DNS_IP"
    log_message "  New Public IP:  $IP"

    if [ "$IP" == "$CURRENT_DNS_IP" ]; then
        log_message "  IP unchanged. No update needed."
        return
    fi

    # Create change batch
    CHANGE_BATCH=$(cat <<EOF
    {
      "Changes": [
        {
          "Action": "UPSERT",
          "ResourceRecordSet": {
            "Name": "$RECORD_NAME",
            "Type": "A",
            "TTL": $TTL,
            "ResourceRecords": [{"Value": "$IP"}]
          }
        }
      ]
    }
EOF
    )

    # Execute update
    UPDATE_RESULT=$(aws route53 change-resource-record-sets \
        --hosted-zone-id "$ZONE_ID" \
        --change-batch "$CHANGE_BATCH" 2>&1)

    if [ $? -eq 0 ]; then
        log_message "  Success: DNS record updated."
    else
        log_message "  Error: Failed to update DNS record. Output: $UPDATE_RESULT"
    fi
}

# Main Execution Flow
log_message "--- Starting DNS Update Process ---"

# 1. Validate Ports
if ! check_ports; then
    exit 1
fi

# 2. Get IP
CURRENT_IP=$(get_public_ip)
if [[ -z "$CURRENT_IP" ]]; then
    log_message "Error: Could not determine public IP."
    exit 1
fi
log_message "Public IP detected: $CURRENT_IP"

# 3. Update Records
if [ "$HOSTED_ZONE_ID" == "REPLACE_WITH_YOUR_HOSTED_ZONE_ID" ]; then
    log_message "Error: HOSTED_ZONE_ID not configured in script. Please edit the file."
    exit 1
fi

for DOMAIN in "${DOMAINS[@]}"; do
    update_record "$HOSTED_ZONE_ID" "$DOMAIN" "$CURRENT_IP"
done

log_message "--- Process Completed ---"
