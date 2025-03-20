// Log when the file is loaded
console.log("modbus_dashboard.js loaded");

// Comprehensive Modbus dashboard with realtime updates
(function() {
    "use strict"; // Strict mode for better error checking
    
    console.log("Modbus dashboard page loaded");
    
    // Variables
    var pollCount = 0;
    var pollInterval = 2000; // ms - longer interval for actual data fetching
    var pollingTimer = null;
    var connections = [];
    var activeFilters = {
        deviceType: "",
        signalType: ""
    };
    var socket = null;
    var currentSort = {
        column: null,
        direction: 'asc'
    };
    var SORT_STORAGE_KEY = 'modbus_dashboard_sort_preferences';
    
    // No fallback data - we'll use the API properly
    
    // Function to update the page with poll count and fetch fresh data
    function updateDashboard() {
        pollCount++;
        
        // Update page title to show poll count - works in all browsers
        document.title = "Modbus Dashboard (Poll: " + pollCount + ")";
        
        // Update the poll count display if it exists
        var pollCountDisplay = document.getElementById('poll-count-display');
        if (pollCountDisplay) {
            pollCountDisplay.textContent = "Poll count: " + pollCount;
        }
        
        // Log to console
        console.log("Polling signals (count: " + pollCount + ") at " + new Date().toISOString());
        
        // If we already have connections data, just update the UI without fetching
        if (connections && connections.length > 0 && pollCount > 1) {
            console.log("Using cached connections data for poll " + pollCount);
            renderDashboard();
            return;
        }
        
        // Fetch fresh data from the server
        fetchModbusData();
    }
    
    // Function to fetch Modbus data from the server
    function fetchModbusData() {
        showLoading(true);
        
        // Prepare headers with CSRF token if available
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token if available
        if (frappe && frappe.csrf_token) {
            headers['X-Frappe-CSRF-Token'] = frappe.csrf_token;
        }
        
        console.log("Fetching Modbus data with headers:", headers);
        
        // Use standard fetch API which works in all modern browsers
        fetch('/api/method/epibus.www.modbus_dashboard.get_modbus_data', {
            method: 'GET',
            headers: headers,
            credentials: 'same-origin'
        })
        .then(function(response) {
            console.log("API response status:", response.status, response.statusText);
            
            if (!response.ok) {
                return response.text().then(function(text) {
                    console.error("Error response body:", text);
                    throw new Error('Network response was not ok: ' + response.statusText);
                });
            }
            
            // Use response.json() but also ensure JSON.parse is used for cross-browser compatibility
            return response.json().catch(function(error) {
                console.error("Error parsing JSON:", error);
                // Fallback to manual JSON parsing if response.json() fails
                return response.text().then(function(text) {
                    console.log("Raw response text:", text);
                    return JSON.parse(text);
                });
            });
        })
        .then(function(data) {
            console.log("API response data:", data);
            
            if (data && data.message) {
                connections = data.message;
                console.log("Fetched " + connections.length + " connections with signals");
                
                // Log details about the connections and signals
                connections.forEach(function(conn, index) {
                    console.log(`Connection ${index + 1}: ${conn.device_name || conn.name}`);
                    console.log(`  Enabled: ${conn.enabled}`);
                    console.log(`  Signals: ${(conn.signals || []).length}`);
                    
                    if (conn.signals && conn.signals.length > 0) {
                        console.log("  Signal details:");
                        conn.signals.forEach(function(signal, sigIndex) {
                            console.log(`    Signal ${sigIndex + 1}: ${signal.signal_name}, Type: ${signal.signal_type}, Value: ${signal.value}`);
                        });
                    }
                });
                
                renderDashboard();
            } else {
                console.error("Invalid data structure received:", data);
                showError("Invalid data received from server");
            }
            showLoading(false);
        })
        .catch(function(error) {
            console.error('Error fetching Modbus data:', error);
            showError("Failed to fetch Modbus data: " + error.message);
            showLoading(false);
        });
    }
    
    // Function to show/hide loading indicator
    function showLoading(show) {
        var loadingElement = document.getElementById('loading');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }
    
    // Function to show error message
    function showError(message) {
        var errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(function() {
                errorElement.style.display = 'none';
            }, 5000);
        }
    }
    
    // Function to render the dashboard with connections and signals
    function renderDashboard() {
        var dashboardGrid = document.getElementById('dashboard-grid');
        if (!dashboardGrid) {
            console.error("Dashboard grid element not found");
            
            // Try to find the container and create the dashboard grid if it doesn't exist
            var container = document.querySelector('.container-fluid');
            if (container) {
                console.log("Container found, creating dashboard grid");
                dashboardGrid = document.createElement('div');
                dashboardGrid.id = 'dashboard-grid';
                dashboardGrid.className = 'row';
                container.appendChild(dashboardGrid);
            } else {
                console.error("Container not found, cannot create dashboard grid");
                return;
            }
        }
        
        // Clear existing content
        dashboardGrid.innerHTML = '';
        
        // Add poll indicator
        addPollIndicator(dashboardGrid);
        
        // Filter connections based on active filters
        var filteredConnections = connections.filter(function(conn) {
            if (activeFilters.deviceType && conn.device_type !== activeFilters.deviceType) {
                return false;
            }
            return true;
        });
        
        // If no connections after filtering, show message
        if (filteredConnections.length === 0) {
            var noDataMsg = document.createElement('div');
            noDataMsg.className = 'col-12 text-center p-5';
            noDataMsg.innerHTML = '<h4>No connections match the current filters</h4>';
            dashboardGrid.appendChild(noDataMsg);
            return;
        }
        
        // Render each connection card
        filteredConnections.forEach(function(connection) {
            var connectionCard = createConnectionCard(connection);
            dashboardGrid.appendChild(connectionCard);
        });
        
        // Apply saved sort preferences to all tables
        if (currentSort.column) {
            var tables = dashboardGrid.querySelectorAll('.signals-container table');
            tables.forEach(function(table) {
                applySavedSortPreferences(table);
            });
        }
    }
    
    // Function to create a connection card
    function createConnectionCard(connection) {
        // Filter signals based on active filters
        var filteredSignals = connection.signals || [];
        if (activeFilters.signalType) {
            filteredSignals = filteredSignals.filter(function(signal) {
                return signal.signal_type === activeFilters.signalType;
            });
        }
        
        // Create card container
        var cardCol = document.createElement('div');
        cardCol.className = 'col-md-6 col-lg-4 mb-4';
        
        // Create card
        var card = document.createElement('div');
        card.className = 'card h-100';
        card.id = 'connection-' + connection.name;
        
        // Card header
        var cardHeader = document.createElement('div');
        cardHeader.className = 'card-header d-flex justify-content-between align-items-center';
        
        var deviceName = document.createElement('h5');
        deviceName.className = 'mb-0';
        deviceName.textContent = connection.device_name || connection.name;
        
        var statusBadge = document.createElement('span');
        statusBadge.className = 'badge ' + (connection.enabled ? 'bg-success' : 'bg-danger');
        statusBadge.textContent = connection.enabled ? 'Enabled' : 'Disabled';
        
        cardHeader.appendChild(deviceName);
        cardHeader.appendChild(statusBadge);
        
        // Card body
        var cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        // Connection details
        var connectionDetails = document.createElement('div');
        connectionDetails.className = 'mb-3';
        connectionDetails.innerHTML =
            '<p class="mb-1"><strong>Type:</strong> ' + (connection.device_type || 'N/A') + '</p>' +
            '<p class="mb-1"><strong>Host:</strong> ' + (connection.host || 'N/A') + '</p>' +
            '<p class="mb-0"><strong>Port:</strong> ' + (connection.port || 'N/A') + '</p>';
        
        // Signals table
        var signalsContainer = document.createElement('div');
        signalsContainer.className = 'signals-container mt-3';
        
        if (filteredSignals.length > 0) {
            var table = document.createElement('table');
            table.className = 'table table-sm table-hover';
            
            // Table header
            var thead = document.createElement('thead');
            thead.innerHTML =
                '<tr>' +
                    '<th class="sortable" data-sort="name">Signal Name <span class="sort-indicator"><i class="fa fa-sort"></i></span></th>' +
                    '<th class="sortable" data-sort="type">Type <span class="sort-indicator"><i class="fa fa-sort"></i></span></th>' +
                    '<th class="sortable" data-sort="value">Value <span class="sort-indicator"><i class="fa fa-sort"></i></span></th>' +
                    '<th class="sortable" data-sort="address">Address <span class="sort-indicator"><i class="fa fa-sort"></i></span></th>' +
                    '<th>Actions</th>' +
                '</tr>';
            
            // Table body
            var tbody = document.createElement('tbody');
            filteredSignals.forEach(function(signal) {
                var row = document.createElement('tr');
                row.id = 'signal-' + signal.name;
                row.dataset.signalId = signal.name;
                // Format value based on signal type
                var formattedValue = formatSignalValue(signal);
                
                // Create action buttons based on signal type
                var actionButtons = createActionButtons(signal);
                
                // Use string concatenation instead of template literals to avoid syntax issues
                row.innerHTML =
                    '<td>' + (signal.signal_name || 'N/A') + '</td>' +
                    '<td><small>' + (signal.signal_type || 'N/A') + '</small></td>' +
                    '<td class="signal-value-cell">' + formattedValue + '</td>' +
                    '<td><code>' + (signal.modbus_address !== undefined ? signal.modbus_address : 'N/A') + '</code></td>' +
                    '<td class="signal-actions">' + actionButtons + '</td>';
                
                tbody.appendChild(row);
            });
            
            table.appendChild(thead);
            table.appendChild(tbody);
            signalsContainer.appendChild(table);
        } else {
            var noSignalsMsg = document.createElement('p');
            noSignalsMsg.className = 'text-center text-muted';
            noSignalsMsg.textContent = 'No signals match the current filters';
            signalsContainer.appendChild(noSignalsMsg);
        }
        
        // Assemble card
        cardBody.appendChild(connectionDetails);
        cardBody.appendChild(signalsContainer);
        
        card.appendChild(cardHeader);
        card.appendChild(cardBody);
        cardCol.appendChild(card);
        
        return cardCol;
    }
    
    // Function to format signal value based on type
    function formatSignalValue(signal) {
        if (signal.value === undefined || signal.value === null) {
            return '<span class="text-muted">N/A</span>';
        }
        
        if (typeof signal.value === 'boolean') {
            return signal.value ?
                '<span class="signal-indicator green">ON</span>' :
                '<span class="signal-indicator red">OFF</span>';
        } else if (typeof signal.value === 'number') {
            return signal.value.toFixed(2);
        } else {
            return signal.value.toString();
        }
    }
    
    // Function to check if a signal type is writable
    function isSignalWritable(signalType) {
        return signalType === "Digital Output Coil" ||
               signalType === "Analog Output Register" ||
               signalType === "Holding Register";
    }
    
    // Function to create action buttons based on signal type
    function createActionButtons(signal) {
        if (!isSignalWritable(signal.signal_type)) {
            return ''; // No buttons for read-only signals
        }
        
        if (signal.signal_type === "Digital Output Coil") {
            // Toggle button for digital outputs
            return '<button class="btn btn-sm btn-outline-primary toggle-signal" data-signal-id="' + signal.name + '">' +
                   'Toggle' +
                   '</button>';
        } else {
            // Input field and set button for analog outputs and holding registers
            var defaultValue = typeof signal.value === 'number' ? signal.value : 0;
            return '<div class="input-group input-group-sm">' +
                   '<input type="number" class="form-control form-control-sm signal-value-input" ' +
                   'data-signal-id="' + signal.name + '" value="' + defaultValue + '">' +
                   '<div class="input-group-append">' +
                   '<button class="btn btn-sm btn-outline-primary set-signal-value" data-signal-id="' + signal.name + '">' +
                   'Set' +
                   '</button>' +
                   '</div>' +
                   '</div>';
        }
    }
    
    // Function to add poll indicator to the page
    function addPollIndicator(container) {
        // Create a poll indicator element
        var pollIndicator = document.createElement('div');
        pollIndicator.id = 'poll-indicator';
        pollIndicator.className = 'col-12 mb-4';
        pollIndicator.style.padding = '15px';
        pollIndicator.style.backgroundColor = '#f0f8ff';
        pollIndicator.style.border = '1px solid #ccc';
        pollIndicator.style.borderRadius = '5px';
        
        // Create indicator content
        var indicatorContent = document.createElement('div');
        indicatorContent.className = 'd-flex justify-content-between align-items-center';
        
        var statusInfo = document.createElement('div');
        
        var heading = document.createElement('h5');
        heading.className = 'mb-1';
        heading.textContent = "Modbus Polling Active";
        statusInfo.appendChild(heading);
        
        var description = document.createElement('p');
        description.className = 'mb-0 text-muted';
        description.textContent = "Auto-refreshing every " + (pollInterval/1000) + " seconds";
        statusInfo.appendChild(description);
        
        var countDisplay = document.createElement('div');
        countDisplay.id = 'poll-count-display';
        countDisplay.className = 'badge bg-primary p-2';
        countDisplay.style.fontSize = '1rem';
        countDisplay.textContent = "Poll count: " + pollCount;
        
        indicatorContent.appendChild(statusInfo);
        indicatorContent.appendChild(countDisplay);
        pollIndicator.appendChild(indicatorContent);
        
        // Add to container
        container.appendChild(pollIndicator);
    }
    
    // Function to setup event listeners for filters and signal actions
    function setupFilterListeners() {
        var deviceTypeFilter = document.getElementById('device-type-filter');
        var signalTypeFilter = document.getElementById('signal-type-filter');
        var refreshButton = document.getElementById('refresh-data');
        var dashboardGrid = document.getElementById('dashboard-grid');
        
        if (deviceTypeFilter) {
            deviceTypeFilter.addEventListener('change', function() {
                activeFilters.deviceType = this.value;
                renderDashboard();
            });
        }
        
        if (signalTypeFilter) {
            signalTypeFilter.addEventListener('change', function() {
                activeFilters.signalType = this.value;
                renderDashboard();
            });
        }
        
        if (refreshButton) {
            refreshButton.addEventListener('click', function() {
                fetchModbusData();
            });
        }
        
        // Event delegation for signal action buttons and table sorting
        if (dashboardGrid) {
            dashboardGrid.addEventListener('click', function(event) {
                // Handle table sorting when clicking on sortable headers
                if (event.target.closest('.sortable') ||
                    (event.target.closest('.sort-indicator') && event.target.closest('th.sortable'))) {
                    
                    // Find the closest sortable header
                    var sortableHeader = event.target.closest('.sortable') ||
                                        event.target.closest('th.sortable');
                    
                    if (sortableHeader) {
                        var column = sortableHeader.getAttribute('data-sort');
                        sortTable(sortableHeader, column);
                    }
                    return;
                }
                
                // Toggle button for digital outputs
                if (event.target.classList.contains('toggle-signal')) {
                    var signalId = event.target.getAttribute('data-signal-id');
                    if (signalId) {
                        toggleSignal(signalId);
                    }
                }
                
                // Set value button for analog outputs and holding registers
                if (event.target.classList.contains('set-signal-value')) {
                    var signalId = event.target.getAttribute('data-signal-id');
                    if (signalId) {
                        var inputElement = document.querySelector('.signal-value-input[data-signal-id="' + signalId + '"]');
                        if (inputElement) {
                            var value = parseFloat(inputElement.value);
                            if (!isNaN(value)) {
                                setSignalValue(signalId, value);
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Function to sort a table based on a column
    function sortTable(headerElement, column) {
        // Find the table that contains this header
        var table = headerElement.closest('table');
        if (!table) return;
        
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Get all rows from the table body
        var rows = Array.from(tbody.querySelectorAll('tr'));
        if (rows.length === 0) return;
        
        // Determine sort direction
        var direction = 'asc';
        
        // If we're already sorting by this column, toggle direction
        if (currentSort.column === column) {
            direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        }
        
        // Update current sort state
        currentSort.column = column;
        currentSort.direction = direction;
        
        // Save sort preferences to localStorage
        saveSortPreferences();
        
        // Update all sort indicators in this table
        var headers = table.querySelectorAll('th.sortable');
        headers.forEach(function(header) {
            var indicator = header.querySelector('.sort-indicator');
            if (indicator) {
                // Reset all indicators
                indicator.innerHTML = '<i class="fa fa-sort"></i>';
            }
        });
        
        // Update the clicked header's indicator
        var clickedIndicator = headerElement.querySelector('.sort-indicator');
        if (clickedIndicator) {
            clickedIndicator.innerHTML = direction === 'asc' ?
                '<i class="fa fa-sort-up"></i>' :
                '<i class="fa fa-sort-down"></i>';
        }
        
        // Sort the table data
        sortTableData(table, column, direction);
    }
    
    // Function to toggle a digital signal
    function toggleSignal(signalId) {
        console.log("Toggling signal:", signalId);
        
        // Show loading indicator
        showLoading(true);
        
        // Prepare headers with CSRF token if available
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token if available
        if (frappe && frappe.csrf_token) {
            headers['X-Frappe-CSRF-Token'] = frappe.csrf_token;
        }
        
        // Call the toggle_signal method
        fetch('/api/method/epibus.epibus.doctype.modbus_signal.modbus_signal.toggle_signal', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                signal_id: signalId
            }),
            credentials: 'same-origin'
        })
        .then(function(response) {
            if (!response.ok) {
                return response.text().then(function(text) {
                    throw new Error('Network response was not ok: ' + text);
                });
            }
            return response.json();
        })
        .then(function(data) {
            console.log("Toggle response:", data);
            if (data && data.message !== undefined) {
                // Update the UI with the new value
                updateSignalValue(signalId, data.message);
            }
            showLoading(false);
        })
        .catch(function(error) {
            console.error('Error toggling signal:', error);
            showError("Failed to toggle signal: " + error.message);
            showLoading(false);
        });
    }
    
    // Function to set a value for an analog or holding register
    function setSignalValue(signalId, value) {
        console.log("Setting signal value:", signalId, value);
        
        // Show loading indicator
        showLoading(true);
        
        // Prepare headers with CSRF token if available
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token if available
        if (frappe && frappe.csrf_token) {
            headers['X-Frappe-CSRF-Token'] = frappe.csrf_token;
        }
        
        // Call the write_signal method
        fetch('/api/method/frappe.client.set_value', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                doctype: 'Modbus Signal',
                name: signalId,
                fieldname: 'float_value',
                value: value
            }),
            credentials: 'same-origin'
        })
        .then(function(response) {
            if (!response.ok) {
                return response.text().then(function(text) {
                    throw new Error('Network response was not ok: ' + text);
                });
            }
            return response.json();
        })
        .then(function(data) {
            console.log("Set value response:", data);
            if (data && data.message) {
                // Update the UI with the new value
                updateSignalValue(signalId, value);
            }
            showLoading(false);
        })
        .catch(function(error) {
            console.error('Error setting signal value:', error);
            showError("Failed to set signal value: " + error.message);
            showLoading(false);
        });
    }
    
    // Function to setup Socket.IO for realtime updates
    function setupRealtimeUpdates() {
        try {
            // Check if frappe.realtime is available (Frappe's Socket.IO wrapper)
            if (frappe && frappe.realtime) {
                console.log("Setting up realtime updates using Frappe's Socket.IO");
                
                // Subscribe to modbus_signal_update events
                frappe.realtime.on('modbus_signal_update', function(data) {
                    console.log("Received realtime update:", data);
                    updateSignalValue(data.signal, data.value);
                });
            } else {
                console.warn("Frappe realtime not available, falling back to polling only");
            }
        } catch (e) {
            console.error("Error setting up realtime updates:", e);
        }
    }
    
    // Function to update a signal value in the UI
    function updateSignalValue(signalId, value) {
        // Find the signal row
        var signalRow = document.querySelector('tr[data-signal-id="' + signalId + '"]');
        if (!signalRow) {
            return;
        }
        
        // Find the value cell
        var valueCell = signalRow.querySelector('.signal-value-cell');
        if (!valueCell) {
            return;
        }
        
        // Update the connections array with the new value
        for (var i = 0; i < connections.length; i++) {
            var signals = connections[i].signals || [];
            for (var j = 0; j < signals.length; j++) {
                if (signals[j].name === signalId) {
                    signals[j].value = value;
                    
                    // Format and update the cell
                    valueCell.innerHTML = formatSignalValue(signals[j]);
                    
                    // Add a highlight effect
                    valueCell.classList.add('bg-light');
                    setTimeout(function() {
                        valueCell.classList.remove('bg-light');
                    }, 1000);
                    
                    return;
                }
            }
        }
    }
    
    // Function to save sort preferences to localStorage
    function saveSortPreferences() {
        try {
            localStorage.setItem(SORT_STORAGE_KEY, JSON.stringify(currentSort));
            console.log("Sort preferences saved:", currentSort);
        } catch (e) {
            console.error("Error saving sort preferences to localStorage:", e);
        }
    }
    
    // Function to load sort preferences from localStorage
    function loadSortPreferences() {
        try {
            var savedSort = localStorage.getItem(SORT_STORAGE_KEY);
            if (savedSort) {
                currentSort = JSON.parse(savedSort);
                console.log("Sort preferences loaded:", currentSort);
                return true;
            }
        } catch (e) {
            console.error("Error loading sort preferences from localStorage:", e);
        }
        return false;
    }
    
    // Function to apply saved sort preferences to a table
    function applySavedSortPreferences(table) {
        if (!table || !currentSort.column) return false;
        
        // Find the header with the matching data-sort attribute
        var header = table.querySelector('th.sortable[data-sort="' + currentSort.column + '"]');
        if (header) {
            // Update the sort indicator
            var indicator = header.querySelector('.sort-indicator');
            if (indicator) {
                indicator.innerHTML = currentSort.direction === 'asc' ?
                    '<i class="fa fa-sort-up"></i>' :
                    '<i class="fa fa-sort-down"></i>';
            }
            
            // Sort the table
            sortTableData(table, currentSort.column, currentSort.direction);
            return true;
        }
        
        return false;
    }
    
    // Function to sort table data without updating the currentSort state
    function sortTableData(table, column, direction) {
        if (!table) return;
        
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Get all rows from the table body
        var rows = Array.from(tbody.querySelectorAll('tr'));
        if (rows.length === 0) return;
        
        // Get column index for sorting
        var headerRow = table.querySelector('thead tr');
        if (!headerRow) return;
        
        var headers = headerRow.querySelectorAll('th');
        var columnIndex = -1;
        
        for (var i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute('data-sort') === column) {
                columnIndex = i;
                break;
            }
        }
        
        if (columnIndex === -1) return;
        
        // Sort the rows
        rows.sort(function(rowA, rowB) {
            var cellA = rowA.cells[columnIndex].textContent.trim();
            var cellB = rowB.cells[columnIndex].textContent.trim();
            
            // Handle numeric values
            if (!isNaN(parseFloat(cellA)) && !isNaN(parseFloat(cellB))) {
                return direction === 'asc' ?
                    parseFloat(cellA) - parseFloat(cellB) :
                    parseFloat(cellB) - parseFloat(cellA);
            }
            
            // Handle text values
            return direction === 'asc' ?
                cellA.localeCompare(cellB) :
                cellB.localeCompare(cellA);
        });
        
        // Remove all existing rows
        while (tbody.firstChild) {
            tbody.removeChild(tbody.firstChild);
        }
        
        // Add sorted rows back to the table
        rows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }
    
    // Function to initialize the dashboard
    function initDashboard() {
        console.log("Initializing Modbus Dashboard");
        console.log("Using polling interval: " + pollInterval + "ms");
        
        // Load saved sort preferences
        loadSortPreferences();
        
        // Setup filter event listeners
        setupFilterListeners();
        
        // Setup realtime updates
        setupRealtimeUpdates();
        
        // Check if we have initial data from the page context
        if (window.initialConnections) {
            console.log("Using initial connections data from page context");
            connections = window.initialConnections;
            renderDashboard();
        } else {
            // Fetch data from API
            console.log("Fetching data from API");
            fetchModbusData();
        }
        
        // Start polling
        console.log("Starting auto-refresh with interval: " + pollInterval + "ms");
        
        // Clear any existing interval to avoid duplicates
        if (pollingTimer) {
            clearInterval(pollingTimer);
        }
        
        // Start new interval - using standard setInterval which works in all browsers
        pollingTimer = setInterval(updateDashboard, pollInterval);
    }
    
    // Function to safely initialize when document is ready
    function domReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    }
    
    // Function to force a cache refresh
    function forceRefresh() {
        // Add a timestamp parameter to the URL to force a cache refresh
        const timestamp = new Date().getTime();
        const currentUrl = window.location.href;
        const separator = currentUrl.indexOf('?') !== -1 ? '&' : '?';
        const newUrl = currentUrl + separator + '_=' + timestamp;
        
        // Only reload if we haven't already added a timestamp
        if (currentUrl.indexOf('_=') === -1) {
            window.location.href = newUrl;
        }
    }
    
    // Initialize when document is ready using a cross-browser approach
    domReady(function() {
        // Force a cache refresh on first load
        if (window.location.href.indexOf('_=') === -1) {
            forceRefresh();
            return;
        }
        
        // Check if we're in a Frappe environment
        if (typeof frappe !== 'undefined') {
            // Use Frappe's ready function if available
            frappe.ready(function() {
                console.log("Initializing dashboard via frappe.ready()");
                initDashboard();
            });
        } else {
            // Fallback to standard DOM ready
            console.log("Initializing dashboard via DOM ready");
            initDashboard();
        }
    });
    
    // Handle page visibility changes to avoid background polling
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // Page is hidden, pause polling
            if (pollingTimer) {
                clearInterval(pollingTimer);
                pollingTimer = null;
                console.log("Polling paused - page hidden");
            }
        } else {
            // Page is visible again, resume polling
            if (!pollingTimer) {
                pollingTimer = setInterval(updateDashboard, pollInterval);
                console.log("Polling resumed - page visible");
            }
        }
    });
    
    // Handle page unload to clean up
    window.addEventListener('beforeunload', function() {
        if (pollingTimer) {
            clearInterval(pollingTimer);
            pollingTimer = null;
        }
        
        // Clean up Socket.IO connection if needed
        if (frappe && frappe.realtime) {
            frappe.realtime.off('modbus_signal_update');
        }
    });
})();