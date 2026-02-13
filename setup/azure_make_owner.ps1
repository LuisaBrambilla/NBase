# Azure Role Assignment Script - Make User Owner of Resource Group
# This script assigns Owner role to a user on a specific resource group

param(
    [Parameter(Mandatory = $true)]
    [string]$UserEmail,
    
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,
    
    [string]$SubscriptionId = "618a82e3-0571-4142-b50d-c8d2c34060ae"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Azure Role Assignment - Owner" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Set subscription
Write-Host "Setting subscription: $SubscriptionId" -ForegroundColor Yellow
az account set --subscription $SubscriptionId

# Get resource group ID
Write-Host "Getting resource group ID..." -ForegroundColor Yellow
$rgId = az group show --name $ResourceGroup --query id -o tsv

if (-not $rgId) {
    Write-Host "✗ Error: Resource group '$ResourceGroup' not found" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Resource group found: $ResourceGroup" -ForegroundColor Green

# Assign Owner role
Write-Host "`nAssigning Owner role to: $UserEmail" -ForegroundColor Yellow

try {
    $assignment = az role assignment create `
        --assignee $UserEmail `
        --role "Owner" `
        --scope $rgId | ConvertFrom-Json
    
    Write-Host "✓ Successfully assigned Owner role!" -ForegroundColor Green
    Write-Host "`nAssignment Details:" -ForegroundColor Cyan
    Write-Host "  Principal ID: $($assignment.principalId)" -ForegroundColor Gray
    Write-Host "  Role: $($assignment.roleDefinitionId.Split('/')[-1])" -ForegroundColor Gray
    Write-Host "  Scope: $($assignment.scope)" -ForegroundColor Gray
    Write-Host "  Created: $($assignment.createdOn)" -ForegroundColor Gray
}
catch {
    Write-Host "✗ Error assigning role: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Verify the assignment
Write-Host "`nVerifying role assignment..." -ForegroundColor Yellow
az role assignment list `
    --resource-group $ResourceGroup `
    --assignee $UserEmail `
    --query "[].{Principal:principalName, Role:roleDefinitionName, Scope:scope}" `
    -o table

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ Role assignment complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "User '$UserEmail' now has Owner permissions on resource group '$ResourceGroup'" -ForegroundColor White
Write-Host "`nOwner permissions include:" -ForegroundColor Yellow
Write-Host "  • Full control over all resources" -ForegroundColor Gray
Write-Host "  • Manage access control (assign roles)" -ForegroundColor Gray
Write-Host "  • View costs and billing" -ForegroundColor Gray
Write-Host "  • Create, update, and delete resources" -ForegroundColor Gray
Write-Host ""
