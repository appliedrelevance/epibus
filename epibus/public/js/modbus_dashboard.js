// modbus_dashboard.js
document.addEventListener("DOMContentLoaded", function () {
    // Connect to Frappe's socket.io system for real-time updates
    var socket = io();
    var connections = [];

    // Helper function to get signal status icon
    function getSignalStatusIcon(signal) {
        const value = signal.value;

        // Digital Input Contact (uses circle icons)
        if (signal.type === "Digital Input Contact") {
            return value ?
                '<i class="fa fa-circle digital-input-true"></i> TRUE' :
                '<i class="fa fa-circle-o digital-input-false"></i> FALSE';
        }

        // Digital Output Coil (uses toggle icons)
        if (signal.type === "Digital Output Coil") {
            return value ?
                '<i class="fa fa-toggle-on digital-output-true"></i> TRUE' :
                '<i class="fa fa-toggle-off digital-output-false"></i> FALSE';
        }

        // For analog signals, just return the value
        return `<span class="value-display">${value}</span>`;
    }

    // Fetch and initialize connections and signals
    function initializeDashboard() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Modbus Connection',
                fields: ['name', 'device_name', 'enabled'],
                filters: { enabled: 1 }
            },
            callback: function (response) {
                if (response.message) {
                    Promise.all(response.message.map(function (conn) {
                        return new Promise(function (resolve) {
                            frappe.call({
                                method: 'frappe.client.get',
                                args: {
                                    doctype: 'Modbus Connection',
                                    name: conn.name
                                },
                                callback: function (r) {
                                    if (r.message) {
                                        var connection = {
                                            id: r.message.name,
                                            name: r.message.device_name,
                                            signals: []
                                        };

                                        // Get signals for this connection
                                        if (r.message.signals) {
                                            r.message.signals.forEach(function (signal) {
                                                connection.signals.push({
                                                    id: signal.name,
                                                    name: signal.signal_name,
                                                    type: signal.signal_type,
                                                    value: signal.digital_value !== undefined ?
                                                        signal.digital_value :
                                                        signal.float_value,
                                                    status: "unknown",
                                                    timestamp: new Date().toLocaleTimeString()
                                                });

                                                // Start monitoring this signal
                                                frappe.call({
                                                    method: 'epibus.utils.signal_monitor.start_monitoring',
                                                    type: 'POST',
                                                    args: {
                                                        signal_name: signal.name
                                                    },
                                                    callback: function (r) {
                                                        if (r.message && r.message.success) {
                                                            console.log('Started monitoring:', signal.name);
                                                        }
                                                    }
                                                });
                                            });
                                        }
                                        resolve(connection);
                                    }
                                }
                            });
                        });
                    })).then(function (results) {
                        connections = results;
                        renderDashboard();
                    });
                }
            }
        });
    }

    // Function to render the dashboard grid
    function renderDashboard() {
        var dashboardGrid = document.getElementById("dashboard-grid");
        if (!dashboardGrid) return;

        dashboardGrid.innerHTML = "";
        connections.forEach(function (connection) {
            // Create connection card
            var cardWrapper = document.createElement("div");
            cardWrapper.className = "col-md-6";
            var card = document.createElement("div");
            card.className = "connection-card";
            var header = document.createElement("h3");
            header.textContent = connection.name;
            card.appendChild(header);

            // Container for signal cards
            var signalsContainer = document.createElement("div");
            connection.signals.forEach(function (signal) {
                var signalCard = document.createElement("div");
                signalCard.className = "signal-card " + signal.type.toLowerCase().replace(/ /g, '-');

                // Create signal content with appropriate status icon
                signalCard.innerHTML = `
                    <strong>Name:</strong> ${signal.name}<br>
                    <strong>Type:</strong> ${signal.type}<br>
                    <strong>Value:</strong> ${getSignalStatusIcon(signal)}<br>
                    <span class="timestamp">Last updated: ${signal.timestamp}</span>
                `;

                // For digital outputs, add a toggle button
                if (signal.type === "Digital Output Coil") {
                    var toggleBtn = document.createElement("button");
                    toggleBtn.textContent = "Toggle";
                    toggleBtn.className = "toggle-digital";
                    toggleBtn.setAttribute("data-signal", signal.id);
                    signalCard.appendChild(toggleBtn);
                }
                signalsContainer.appendChild(signalCard);
            });
            card.appendChild(signalsContainer);
            cardWrapper.appendChild(card);
            dashboardGrid.appendChild(cardWrapper);
        });
    }

    // Initialize dashboard
    initializeDashboard();

    // Listen for real-time updates via websocket
    socket.on("modbus_signal_update", function (data) {
        // Find and update the signal
        connections.forEach(function (connection) {
            connection.signals.forEach(function (signal) {
                if (signal.id === data.signal) {
                    signal.value = data.value;
                    signal.timestamp = frappe.datetime.now_time();
                    signal.status = "active";
                }
            });
        });
        // Re-render dashboard with updated data
        renderDashboard();
    });

    // Event listener for digital signal toggle buttons
    document.addEventListener("click", function (e) {
        if (e.target && e.target.classList.contains("toggle-digital")) {
            var signalName = e.target.getAttribute("data-signal");
            if (signalName) {
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Modbus Signal',
                        name: signalName
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.call({
                                method: 'epibus.epibus.doctype.modbus_signal.modbus_signal.toggle_signal',
                                args: {
                                    signal: signalName
                                },
                                callback: function (r) {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: 'Signal toggled successfully',
                                            indicator: 'green'
                                        });
                                    }
                                }
                            });
                        }
                    }
                });
            }
        }
    });
});
