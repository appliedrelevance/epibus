// Test script to verify modbus_dashboard.js functionality
const fs = require('fs');
const path = require('path');

// Log test start
console.log('Starting modbus_dashboard.js test...');

// Read the updated JavaScript file
const jsFilePath = path.join(__dirname, 'epibus', 'public', 'js', 'modbus_dashboard.js');
const jsContent = fs.readFileSync(jsFilePath, 'utf8');

// Check for key functions that should be present in the updated file
const requiredFunctions = [
    'fetchModbusData',
    'renderDashboard',
    'createConnectionCard',
    'formatSignalValue',
    'setupRealtimeUpdates',
    'updateSignalValue'
];

let allFunctionsFound = true;
const missingFunctions = [];

requiredFunctions.forEach(func => {
    if (!jsContent.includes(func)) {
        allFunctionsFound = false;
        missingFunctions.push(func);
    }
});

if (allFunctionsFound) {
    console.log('✅ All required functions found in modbus_dashboard.js');
} else {
    console.log('❌ Missing functions in modbus_dashboard.js:', missingFunctions.join(', '));
}

// Check for cross-browser compatibility
const crossBrowserFeatures = [
    'document.addEventListener',
    'fetch(',
    'JSON.parse',
    'querySelector',
    'createElement'
];

let allFeaturesFound = true;
const missingFeatures = [];

crossBrowserFeatures.forEach(feature => {
    if (!jsContent.includes(feature)) {
        allFeaturesFound = false;
        missingFeatures.push(feature);
    }
});

if (allFeaturesFound) {
    console.log('✅ All cross-browser features found in modbus_dashboard.js');
} else {
    console.log('❌ Missing cross-browser features in modbus_dashboard.js:', missingFeatures.join(', '));
}

// Read the updated CSS file
const cssFilePath = path.join(__dirname, 'epibus', 'public', 'css', 'modbus_dashboard.css');
const cssContent = fs.readFileSync(cssFilePath, 'utf8');

// Check for key CSS selectors that should be present in the updated file
const requiredSelectors = [
    '.signal-indicator',
    '.signal-value-cell',
    '.signals-container',
    '@media (max-width: 768px)',
    '@-moz-document',
    '@supports (-webkit-appearance:none)'
];

let allSelectorsFound = true;
const missingSelectors = [];

requiredSelectors.forEach(selector => {
    if (!cssContent.includes(selector)) {
        allSelectorsFound = false;
        missingSelectors.push(selector);
    }
});

if (allSelectorsFound) {
    console.log('✅ All required CSS selectors found in modbus_dashboard.css');
} else {
    console.log('❌ Missing CSS selectors in modbus_dashboard.css:', missingSelectors.join(', '));
}

console.log('\nSummary:');
console.log('- JavaScript functions:', allFunctionsFound ? 'All present ✅' : 'Some missing ❌');
console.log('- Cross-browser features:', allFeaturesFound ? 'All present ✅' : 'Some missing ❌');
console.log('- CSS selectors:', allSelectorsFound ? 'All present ✅' : 'Some missing ❌');

console.log('\nTest completed.');