document.addEventListener('DOMContentLoaded', function() {
    // Initialize Monaco Editor for JSON Schema
    require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.43.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
        window.schemaEditor = monaco.editor.create(document.getElementById('schemaEditor'), {
            value: getDefaultSchema(),
            language: 'json',
            theme: 'vs-light',
            automaticLayout: true,
            minimap: { enabled: false }
        });
    });

    // Initialize UI state
    initializeUI();
    loadSavedTemplates();
    loadSavedSettings();

    // Event listeners
    document.getElementById('apiProvider').addEventListener('change', toggleAzureSettings);
    document.getElementById('temperature').addEventListener('input', updateTemperatureValue);
    document.getElementById('fileUpload').addEventListener('change', handleFileUpload);
    document.getElementById('extractBtn').addEventListener('click', extractData);
    document.getElementById('saveTemplateBtn').addEventListener('click', showSaveTemplateModal);
    document.getElementById('confirmSaveTemplate').addEventListener('click', saveTemplate);
    document.getElementById('validateSchemaBtn').addEventListener('click', validateSchema);
    document.getElementById('resetSchemaBtn').addEventListener('click', resetSchema);
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('copyResultsBtn').addEventListener('click', copyResults);
    document.getElementById('downloadResultsBtn').addEventListener('click', downloadResults);
    document.getElementById('newTemplateBtn').addEventListener('click', createNewTemplate);
});

// Default schema
function getDefaultSchema() {
    return JSON.stringify({
        "vendor_name": {
            "description": "Legal name of the vendor/seller",
            "type": "str"
        },
        "vendor_address": {
            "description": "Complete postal address of the vendor",
            "type": "str"
        },
        "delivery_address": {
            "description": "Complete delivery address if different from billing address",
            "type": "str"
        },
        "product_names": {
            "description": "List of all product/service names in the invoice",
            "type": "List[str]"
        },
        "product_prices": {
            "description": "List of prices corresponding to each product/service",
            "type": "List[float]"
        },
        "product_quantities": {
            "description": "List of quantities corresponding to each product/service",
            "type": "List[float]"
        },
        "tax_details": {
            "description": "Tax breakdown with CGST/SGST/IGST details including rate and amount",
            "type": "Dict",
            "properties": {
                "CGST": {
                    "description": "CGST tax details",
                    "type": "Dict",
                    "properties": {
                        "percentage": {
                            "description": "Tax rate percentage",
                            "type": "float"
                        },
                        "amount": {
                            "description": "Tax amount in currency",
                            "type": "float"
                        }
                    }
                },
                "SGST": {
                    "description": "SGST tax details",
                    "type": "Dict",
                    "properties": {
                        "percentage": {
                            "description": "Tax rate percentage",
                            "type": "float"
                        },
                        "amount": {
                            "description": "Tax amount in currency",
                            "type": "float"
                        }
                    }
                },
                "IGST": {
                    "description": "IGST tax details",
                    "type": "Dict",
                    "properties": {
                        "percentage": {
                            "description": "Tax rate percentage",
                            "type": "float"
                        },
                        "amount": {
                            "description": "Tax amount in currency",
                            "type": "float"
                        }
                    }
                }
            }
        },
        "discount": {
            "description": "Discount details including percentage and amount",
            "type": "Dict",
            "properties": {
                "percentage": {
                    "description": "Discount percentage",
                    "type": "float"
                },
                "amount": {
                    "description": "Discount amount in currency",
                    "type": "float"
                }
            }
        },
        "invoice_total": {
            "description": "Final invoice amount including all taxes",
            "type": "float"
        },
        "total_before_taxes": {
            "description": "Subtotal amount before applying taxes",
            "type": "float"
        },
        "invoice_date": {
            "description": "Date of invoice issuance in DD/MM/YYYY format",
            "type": "str"
        },
        "invoice_number": {
            "description": "Unique invoice reference number",
            "type": "str"
        },
        "gst_registration_number": {
            "description": "GST identification number of the vendor",
            "type": "str"
        }
    }, null, 2);
}

// Initialize UI state
function initializeUI() {
    toggleAzureSettings();
    updateTemperatureValue();
}

// Toggle Azure-specific settings based on API provider selection
function toggleAzureSettings() {
    const provider = document.getElementById('apiProvider').value;
    const azureSettings = document.querySelectorAll('.azure-setting');
    
    azureSettings.forEach(element => {
        element.style.display = provider === 'azure' ? 'block' : 'none';
    });
}

// Update temperature value display
function updateTemperatureValue() {
    const value = document.getElementById('temperature').value;
    document.getElementById('temperatureValue').textContent = value;
}

// Handle file upload
function handleFileUpload(event) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    
    Array.from(event.target.files).forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span class="file-name">${file.name}</span>
            <span class="remove-file"><i class="bi bi-x-circle"></i></span>
        `;
        
        fileItem.querySelector('.remove-file').addEventListener('click', function() {
            fileItem.remove();
            // Note: This doesn't actually remove the file from the input
            // For a complete solution, you'd need to create a new FileList
        });
        
        fileList.appendChild(fileItem);
    });
}

// Extract data from files
async function extractData() {
    const formData = new FormData();
    const files = document.getElementById('fileUpload').files;
    
    if (files.length === 0) {
        alert('Please upload at least one file.');
        return;
    }
    
    // Add files to form data
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // Add other form fields
    formData.append('prompt', document.getElementById('promptInput').value);
    formData.append('api_provider', document.getElementById('apiProvider').value);
    formData.append('api_key', document.getElementById('apiKey').value);
    formData.append('model', document.getElementById('model').value);
    formData.append('temperature', document.getElementById('temperature').value);
    formData.append('max_tokens', document.getElementById('maxTokens').value);
    
    // Add schema definition (optional)
    try {
        const schemaValue = window.schemaEditor.getValue();
        if (schemaValue && schemaValue.trim() !== '') {
            const parsedSchema = JSON.parse(schemaValue);
            formData.append('schema_definition', JSON.stringify(parsedSchema));
        }
    } catch (error) {
        alert('Invalid schema JSON: ' + error.message);
        return;
    }
    
    // Add Azure-specific fields if needed
    if (document.getElementById('apiProvider').value === 'azure') {
        formData.append('azure_endpoint', document.getElementById('azureEndpoint').value);
        formData.append('azure_deployment', document.getElementById('azureDeployment').value);
        formData.append('api_version', document.getElementById('apiVersion').value);
    }
    
    // Show loading state
    document.getElementById('extractBtn').disabled = true;
    document.getElementById('extractBtn').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    try {
        const response = await fetch('http://localhost:8000/api/extract/files', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        alert('Error extracting data: ' + error.message);
    } finally {
        // Reset button state
        document.getElementById('extractBtn').disabled = false;
        document.getElementById('extractBtn').textContent = 'Extract Data';
    }
}

// Display extraction results
function displayResults(data) {
    // Show results section
    document.getElementById('resultsSection').style.display = 'flex';
    
    // Display JSON results
    const resultsJson = document.getElementById('resultsJson');
    resultsJson.textContent = JSON.stringify(data.data, null, 2);
    
    // Display usage metrics
    const usageMetrics = document.getElementById('usageMetrics');
    usageMetrics.innerHTML = '';
    
    // Add file metrics
    data.usage.files.forEach(file => {
        const fileCard = document.createElement('div');
        fileCard.className = 'card usage-card mb-3';
        
        let metricsHtml = '';
        file.page_metrics.forEach(metric => {
            metricsHtml += `
                <div class="usage-metric">
                    <span class="usage-metric-label">Page ${metric.page_number}</span>
                    <span>${metric.total_tokens} tokens ($${metric.total_cost.toFixed(4)})</span>
                </div>
            `;
        });
        
        fileCard.innerHTML = `
            <div class="card-header">
                ${file.file_name}
            </div>
            <div class="card-body">
                ${metricsHtml}
                <div class="usage-metric">
                    <span class="usage-metric-label">Total Cost</span>
                    <span>$${file.total_cost.toFixed(4)}</span>
                </div>
            </div>
        `;
        
        usageMetrics.appendChild(fileCard);
    });
    
    // Add total metrics
    const totalCard = document.createElement('div');
    totalCard.className = 'card';
    totalCard.innerHTML = `
        <div class="card-header bg-primary text-white">
            Summary
        </div>
        <div class="card-body">
            <div class="usage-metric">
                <span class="usage-metric-label">Files Processed</span>
                <span>${data.usage.file_count}</span>
            </div>
            <div class="usage-metric">
                <span class="usage-metric-label">Successful Extractions</span>
                <span>${data.usage.successful_extractions}</span>
            </div>
            <div class="usage-metric">
                <span class="usage-metric-label">Total Cost</span>
                <span>$${data.usage.total_cost.toFixed(4)}</span>
            </div>
        </div>
    `;
    
    usageMetrics.appendChild(totalCard);
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Show save template modal
function showSaveTemplateModal() {
    const modal = new bootstrap.Modal(document.getElementById('saveTemplateModal'));
    modal.show();
}

// Save template to local storage
function saveTemplate() {
    const templateName = document.getElementById('templateName').value.trim();
    
    if (!templateName) {
        alert('Please enter a template name.');
        return;
    }
    
    const templates = JSON.parse(localStorage.getItem('extractionTemplates') || '{}');
    
    templates[templateName] = {
        prompt: document.getElementById('promptInput').value,
        schema: window.schemaEditor.getValue()
    };
    
    localStorage.setItem('extractionTemplates', JSON.stringify(templates));
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('saveTemplateModal')).hide();
    
    // Refresh templates list
    loadSavedTemplates();
    
    // Clear template name input
    document.getElementById('templateName').value = '';
    
    // Show confirmation message
    alert(`Template "${templateName}" saved successfully with both prompt and schema.`);
}

// Load saved templates from local storage
function loadSavedTemplates() {
    const templatesList = document.getElementById('savedTemplatesList');
    templatesList.innerHTML = '';
    
    const templates = JSON.parse(localStorage.getItem('extractionTemplates') || '{}');
    
    Object.keys(templates).forEach(name => {
        const templateItem = document.createElement('li');
        templateItem.className = 'nav-item';
        templateItem.innerHTML = `
            <div class="template-item">
                <span class="template-name">${name}</span>
                <span class="template-info text-muted small ms-2">(prompt + schema)</span>
                <span class="delete-template text-danger"><i class="bi bi-trash"></i></span>
            </div>
        `;
        
        // Load template on click
        templateItem.querySelector('.template-name').addEventListener('click', function() {
            loadTemplate(name);
        });
        
        // Delete template
        templateItem.querySelector('.delete-template').addEventListener('click', function(e) {
            e.stopPropagation();
            deleteTemplate(name);
        });
        
        templatesList.appendChild(templateItem);
    });
}

// Load a template
function loadTemplate(name) {
    const templates = JSON.parse(localStorage.getItem('extractionTemplates') || '{}');
    const template = templates[name];
    
    if (template) {
        document.getElementById('promptInput').value = template.prompt;
        window.schemaEditor.setValue(template.schema);
    }
}

// Delete a template
function deleteTemplate(name) {
    if (confirm(`Are you sure you want to delete the template "${name}"?`)) {
        const templates = JSON.parse(localStorage.getItem('extractionTemplates') || '{}');
        delete templates[name];
        localStorage.setItem('extractionTemplates', JSON.stringify(templates));
        loadSavedTemplates();
    }
}

// Create new template (clear form)
function createNewTemplate() {
    document.getElementById('promptInput').value = '';
    window.schemaEditor.setValue(getDefaultSchema());
}

// Validate schema JSON
function validateSchema() {
    try {
        const schemaValue = window.schemaEditor.getValue();
        if (!schemaValue || schemaValue.trim() === '') {
            alert('Schema is empty, but that\'s okay.');
            return;
        }
        
        // Parse the JSON
        JSON.parse(schemaValue);
        alert('Schema is valid JSON.');
    } catch (error) {
        if (error.message === 'Unexpected end of JSON input') {
            alert('Schema appears to be incomplete. Please check your JSON structure.');
        } else {
            alert('Invalid JSON: ' + error.message);
        }
    }
}

// Reset schema to default
function resetSchema() {
    if (confirm('Are you sure you want to reset the schema to default?')) {
        window.schemaEditor.setValue(getDefaultSchema());
    }
}

// Save API settings to local storage
function saveSettings() {
    const settings = {
        apiProvider: document.getElementById('apiProvider').value,
        apiKey: document.getElementById('apiKey').value,
        model: document.getElementById('model').value,
        temperature: document.getElementById('temperature').value,
        maxTokens: document.getElementById('maxTokens').value,
        azureEndpoint: document.getElementById('azureEndpoint').value,
        azureDeployment: document.getElementById('azureDeployment').value,
        apiVersion: document.getElementById('apiVersion').value
    };
    
    localStorage.setItem('extractionSettings', JSON.stringify(settings));
    alert('Settings saved successfully.');
}

// Load saved settings from local storage
function loadSavedSettings() {
    const settings = JSON.parse(localStorage.getItem('extractionSettings') || '{}');
    
    if (settings.apiProvider) document.getElementById('apiProvider').value = settings.apiProvider;
    if (settings.apiKey) document.getElementById('apiKey').value = settings.apiKey;
    if (settings.model) document.getElementById('model').value = settings.model;
    if (settings.temperature) {
        document.getElementById('temperature').value = settings.temperature;
        updateTemperatureValue();
    }
    if (settings.maxTokens) document.getElementById('maxTokens').value = settings.maxTokens;
    if (settings.azureEndpoint) document.getElementById('azureEndpoint').value = settings.azureEndpoint;
    if (settings.azureDeployment) document.getElementById('azureDeployment').value = settings.azureDeployment;
    if (settings.apiVersion) document.getElementById('apiVersion').value = settings.apiVersion;
    
    toggleAzureSettings();
}

// Copy results to clipboard
function copyResults() {
    const resultsText = document.getElementById('resultsJson').textContent;
    navigator.clipboard.writeText(resultsText).then(() => {
        alert('Results copied to clipboard.');
    }).catch(err => {
        console.error('Failed to copy results: ', err);
        alert('Failed to copy results to clipboard.');
    });
}

// Download results as JSON file
function downloadResults() {
    const resultsText = document.getElementById('resultsJson').textContent;
    if (!resultsText) {
        alert('No results to download.');
        return;
    }
    
    const blob = new Blob([resultsText], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'extraction_results.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}