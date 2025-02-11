// modbus_dashboard.js
document.addEventListener("DOMContentLoaded", function () {
    // Connect to Frappe's socket.io system for real-time updates
    var socket = io();

    // Sample data structure representing connections and signals
    var connections = [
        {
            id: 1, name: "Connection A", signals: [
                { id: 1, type: "digital", value: 0, status: "inactive", timestamp: new Date().toLocaleTimeString() },
                { id: 2, type: "analog", value: 3.7, status: "active", timestamp: new Date().toLocaleTimeString() }
            ]
        },
        {
            id: 2, name: "Connection B", signals: [
                { id: 3, type: "holding", value: 100, status: "active", timestamp: new Date().toLocaleTimeString() }
            ]
        }
    ];

    // Function to render the dashboard grid
    function renderDashboard() {
        var dashboardGrid = document.getElementById("dashboard-grid");
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
                signalCard.className = "signal-card " + signal.type + " " + (signal.status === "active" ? "active" : "inactive");
                signalCard.innerHTML =
                    "<strong>Type:</strong> " + signal.type + "<br>" +
                    "<strong>Value:</strong> " + signal.value + "<br>" +
                    "<strong>Status:</strong> " + signal.status + "<br>" +
                    "<strong>Time:</strong> " + signal.timestamp;
                // For digital signals, add a toggle button
                if (signal.type === "digital") {
                    var toggleBtn = document.createElement("button");
                    toggleBtn.textContent = "Toggle";
                    toggleBtn.className = "btn btn-sm btn-outline-primary toggle-digital";
                    toggleBtn.setAttribute("data-id", signal.id);
                    signalCard.appendChild(document.createElement("br"));
                    signalCard.appendChild(toggleBtn);
                }
                signalsContainer.appendChild(signalCard);
            });
            card.appendChild(signalsContainer);
            cardWrapper.appendChild(card);
            dashboardGrid.appendChild(cardWrapper);
        });
    }

    renderDashboard();

    // Listen for real-time updates via websocket
    socket.on("modbus_signal_update", function (data) {
        // Expected data format: { connection_id, signal: { id, value, status } }
        connections.forEach(function (connection) {
            if (connection.id === data.connection_id) {
                connection.signals.forEach(function (signal) {
                    if (signal.id === data.signal.id) {
                        signal.value = data.signal.value;
                        signal.status = data.signal.status;
                        signal.timestamp = new Date().toLocaleTimeString();
                    }
                });
            }
        });
        // Re-render dashboard with updated data
        renderDashboard();
    });

    // Event listener for digital signal toggle buttons
    document.addEventListener("click", function (e) {
        if (e.target && e.target.classList.contains("toggle-digital")) {
            var signalId = parseInt(e.target.getAttribute("data-id"), 10);
            console.log("Toggle digital signal:", signalId);
            // Here, you can add code to send a request via socket or Frappe call
            // For example: socket.emit("toggle_signal", { signal_id: signalId });
        }
    });

    // Time Series Chart for historical data (using frappe-charts)
    var chart = new frappe.Chart("#time-series-chart", {
        data: {
            labels: [],
            datasets: [
                {
                    name: "Signal Value",
                    chartType: 'line',
                    values: []
                }
            ]
        },
        title: "Signal History",
        type: 'line',
        height: 250,
        colors: ['#7cd6fd']
    });

    // Time range selector event
    document.querySelectorAll("[data-range]").forEach(function (button) {
        button.addEventListener("click", function () {
            var range = this.getAttribute("data-range");
            console.log("Selected time range:", range);
            // Fetch historical data for the selected time range with appropriate API call
            // After retrieval, update chart.data and call chart.update()
        });
    });

    // Export data functionality
    document.getElementById("export-data").addEventListener("click", function () {
        console.log("Exporting historical data...");
        // Code to export data as CSV or JSON can be implemented here
    });
});
