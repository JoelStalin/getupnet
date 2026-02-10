<#
.SYNOPSIS
    Management script for GetUpNet ISP Project
.DESCRIPTION
    Provides shortcuts for Docker operations, tests, and tools.
.EXAMPLE
    .\manage.ps1 shell         # Enter Odoo container
    .\manage.ps1 logs          # Tail logs
    .\manage.ps1 test          # Run all tests
    .\manage.ps1 aws-check     # Run AWS CLI check inside container
    .\manage.ps1 mikrotik list # List routers
#>

param (
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Command = "help",

    [Parameter(Mandatory=$false, Position=1)]
    [string]$Arg1 = "",

    [Parameter(Mandatory=$false, Position=2)]
    [string]$Arg2 = ""
)

$Container = "odoo"

function Show-Help {
    Write-Host "Usage: .\manage.ps1 <command> [args]" -ForegroundColor Cyan
    Write-Host "Commands:"
    Write-Host "  up               Start containers (detached)"
    Write-Host "  down             Stop containers"
    Write-Host "  restart          Restart Odoo container"
    Write-Host "  build            Rebuild Docker images"
    Write-Host "  shell            Open bash shell in Odoo container"
    Write-Host "  logs             Tail Odoo logs"
    Write-Host "  test [path]      Run pytest (default: tests/)"
    Write-Host "  selenium         Run Selenium E2E tests"
    Write-Host "  endpoints        Run endpoint health check"
    Write-Host "  aws <cmd>        Run AWS CLI command inside container"
    Write-Host "  mikrotik <cmd>   Run MikroTik manager (list, jobs, run)"
}

if ($Command -eq "up") {
    docker compose up -d
}
elseif ($Command -eq "down") {
    docker compose down
}
elseif ($Command -eq "restart") {
    docker compose restart $Container
}
elseif ($Command -eq "build") {
    docker compose up -d --build
}
elseif ($Command -eq "shell") {
    docker compose exec -it $Container bash
}
elseif ($Command -eq "logs") {
    docker compose logs -f $Container
}
elseif ($Command -eq "test") {
    $TestPath = if ($Arg1) { $Arg1 } else { "/mnt/tests" }
    docker compose exec $Container pytest $TestPath
}
elseif ($Command -eq "selenium") {
    # Ensure tool is executable or run with python
    # We run it from host, assuming python is installed on host OR running strictly inside container?
    # The plan said wrapper runs inside container OR locally. 
    # Let's run it inside container to use container environment.
    docker compose exec $Container python3 /mnt/extra-addons/../tools/run_selenium.py --url http://odoo:8069 --remote http://selenium:4444/wd/hub
}
elseif ($Command -eq "endpoints") {
    docker compose exec $Container python3 /mnt/extra-addons/../tools/test_endpoints.py --url http://localhost:8069
}
elseif ($Command -eq "aws") {
    # Pass all remaining args to aws
    # Note: parsing args in PS can be tricky, simplified here
    docker compose exec $Container aws $Arg1 $Arg2
}
elseif ($Command -eq "mikrotik") {
    docker compose exec $Container python3 /mnt/extra-addons/../tools/mikrotik_manager.py $Arg1 $Arg2
}
else {
    Show-Help
}
