
document.addEventListener("DOMContentLoaded", () => {

    // Checkout Dynamic Price Calculations
    const checkoutForm = document.getElementById("checkoutForm");
    if (checkoutForm) {
        setupCheckoutCalculator();
    }

    // Interactive Rates & Availability Calendar
    const calendarContainer = document.getElementById("calendarContainer");
    if (calendarContainer) {
        setupHotelCalendar();
    }
});

/**
 * Handles payment tabs toggling and recalculates pricing totals dynamically
 * when the user selects or deselects optional services or promo codes.
 */
function setupCheckoutCalculator() {
    const servicesCheckboxes = document.querySelectorAll(".service_cb");
    const roomCostElement = document.getElementById("baseRoomCost");
    const subtotalElement = document.getElementById("summarySubtotal");
    const discountElement = document.getElementById("summaryDiscount");
    const totalElement = document.getElementById("summaryTotal");
    const promoInput = document.getElementById("promoCodeInput");
    const promoApplyBtn = document.getElementById("applyPromoBtn");
    const promoDisplayInfo = document.getElementById("promoDisplayInfo");

    const hotelEcoLevel = parseInt(document.getElementById("hotelEcoLevel")?.value || "0");
    const roomCost = parseFloat(roomCostElement?.dataset?.cost || "0");

    let promoDiscountPercent = 0.0;

    // Initialize checkout calculation
    recalculateCheckoutTotal();

    // Event listener for services checkboxes
    servicesCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            recalculateCheckoutTotal();
        });
    });

    // Dummy client-side coupon promotion validation
    if (promoApplyBtn) {
        promoApplyBtn.addEventListener("click", () => {
            const code = promoInput.value.trim().toUpperCase();
            if (!code) return;

            // Simulating API validation for demonstration code rules
            if (code === "MARRIOTT20" || code === "TOKYO15") {
                promoDiscountPercent = code === "MARRIOTT20" ? 20.0 : 15.0;
                promoDisplayInfo.innerText = `Coupon ${code} applied successfully: ${promoDiscountPercent}% discount!`;
                promoDisplayInfo.className = "promo_msg_success";
            } else {
                promoDiscountPercent = 0.0;
                promoDisplayInfo.innerText = "Invalid coupon code.";
                promoDisplayInfo.className = "promo_msg_error";
            }
            recalculateCheckoutTotal();
        });
    }

    // Function to calculate totals in real-time
    function recalculateCheckoutTotal() {
        // Calculate services subtotal
        let servicesTotal = 0.0;
        servicesCheckboxes.forEach(cb => {
            if (cb.checked) {
                servicesTotal += parseFloat(cb.dataset.price);
            }
        });

        const subtotal = roomCost + servicesTotal;
        let totalDiscount = 0.0;

        // Apply promo code discount
        if (promoDiscountPercent > 0.0) {
            totalDiscount += subtotal * (promoDiscountPercent / 100.0);
        }

        // Apply Eco-tax break discount if hotel has sustainability level >= 4 (10% off)
        let isEcoFriendly = hotelEcoLevel >= 4;
        if (isEcoFriendly) {
            totalDiscount += subtotal * 0.10;
        }

        const grandTotal = Math.max(0.0, subtotal - totalDiscount);

        // Update display text fields
        if (subtotalElement) subtotalElement.innerText = `$${subtotal.toFixed(2)}`;
        if (discountElement) discountElement.innerText = `-$${totalDiscount.toFixed(2)}`;
        if (totalElement) totalElement.innerText = `$${grandTotal.toFixed(2)}`;

        // Also update optional services text inside the Invoice summary
        const summaryServicesElement = document.getElementById("summaryServices");
        if (summaryServicesElement) {
            summaryServicesElement.innerText = `$${servicesTotal.toFixed(2)}`;
        }
    }

    // Tab Selection for Credit Card or PayPal
    const payTabs = document.querySelectorAll(".payment_tab");
    const payPanels = document.querySelectorAll(".payment_details_panel");
    const payMethodInput = document.getElementById("selectedPaymentMethod");
    const cardInput = document.getElementById("cardNumberInput");
    const paypalInput = document.getElementById("paypalEmailInput");

    payTabs.forEach(tab => {
        tab.addEventListener("click", (e) => {
            e.preventDefault();
            const method = tab.dataset.method; // "Card" or "PayPal"

            // Set active states on buttons
            payTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            // Set active states on forms
            payPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === `payPanel${method}`) {
                    panel.classList.add("active");
                }
            });

            // Update hidden form selector
            if (payMethodInput) payMethodInput.value = method;

            // Make inputs required depending on selection
            if (method === "Card") {
                if (cardInput) cardInput.required = true;
                if (paypalInput) paypalInput.required = false;
            } else {
                if (cardInput) cardInput.required = false;
                if (paypalInput) paypalInput.required = true;
            }
        });
    });
}

/**
 * Manages the calendar monthly loading, UI grid drawing,
 * and date selection logics (check-in and check-out selection).
 */
function setupHotelCalendar() {
    const calendarContainer = document.getElementById("calendarContainer");
    const hotelId = calendarContainer.dataset.hotelId;
    const roomSelect = document.getElementById("calendarRoomSelect");
    const prevMonthBtn = document.getElementById("calendarPrevMonth");
    const nextMonthBtn = document.getElementById("calendarNextMonth");
    const calendarMonthTitle = document.getElementById("calendarMonthTitle");
    const checkInInput = document.getElementById("sidebarCheckIn");
    const checkOutInput = document.getElementById("sidebarCheckOut");
    const nightsDisplay = document.getElementById("sidebarNights");
    const totalDisplay = document.getElementById("sidebarEstTotal");
    const sidebarBookBtn = document.getElementById("sidebarBookBtn");

    // Default to current year and month
    let currentYear = new Date().getFullYear();
    let currentMonth = new Date().getMonth() + 1; // 1-indexed

    // Date range selection state
    let selectedCheckIn = null; // Date object
    let selectedCheckOut = null; // Date object
    let calendarDaysData = []; // Store loaded days details

    // Initialize calendar trigger
    if (roomSelect) {
        roomSelect.addEventListener("change", () => {
            // Reset selection when changing room type
            resetDateSelection();
            loadCalendarData();
        });
        loadCalendarData();
    }

    if (prevMonthBtn && nextMonthBtn) {
        prevMonthBtn.addEventListener("click", () => {
            currentMonth--;
            if (currentMonth < 1) {
                currentMonth = 12;
                currentYear--;
            }
            loadCalendarData();
        });

        nextMonthBtn.addEventListener("click", () => {
            currentMonth++;
            if (currentMonth > 12) {
                currentMonth = 1;
                currentYear++;
            }
            loadCalendarData();
        });
    }

    function resetDateSelection() {
        selectedCheckIn = null;
        selectedCheckOut = null;
        if (checkInInput) checkInInput.value = "";
        if (checkOutInput) checkOutInput.value = "";
        if (nightsDisplay) nightsDisplay.innerText = "0";
        if (totalDisplay) totalDisplay.innerText = "$0.00";
        if (sidebarBookBtn) sidebarBookBtn.disabled = true;
    }

    /**
     * Fetches dynamic dates, pricing and availability status from the Flask API
     */
    function loadCalendarData() {
        const roomId = roomSelect.value;
        if (!roomId) {
            calendarContainer.innerHTML = "<p class='text_muted'>Please select a room type to view calendar.</p>";
            return;
        }

        // Show loading state
        calendarContainer.innerHTML = "<div class='text_muted'>Loading calendar data...</div>";

        fetch(`/hotel/${hotelId}/calendar?room_id=${roomId}&year=${currentYear}&month=${currentMonth}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    calendarContainer.innerHTML = `<div class='alert_box alert_error'>${data.error}</div>`;
                    return;
                }
                calendarDaysData = data.days;
                renderCalendarGrid(data);
            })
            .catch(err => {
                console.error("Error loading calendar details:", err);
                calendarContainer.innerHTML = "<div class='alert_box alert_error'>Failed to load calendar data.</div>";
            });
    }

    /**
     * Renders the Sun-Sat day headers and 1-31 grid cells
     */
    function renderCalendarGrid(data) {
        const monthsNames = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];

        // Update month-year header text
        if (calendarMonthTitle) {
            calendarMonthTitle.innerText = `${monthsNames[data.month - 1]} ${data.year}`;
        }

        let html = `
            <div class="calendar_grid">
                <div class="calendar_day_header">Sun</div>
                <div class="calendar_day_header">Mon</div>
                <div class="calendar_day_header">Tue</div>
                <div class="calendar_day_header">Wed</div>
                <div class="calendar_day_header">Thu</div>
                <div class="calendar_day_header">Fri</div>
                <div class="calendar_day_header">Sat</div>
        `;

        // Determine starting day of week for the first day of the month
        const firstDayStr = `${data.year}-${String(data.month).padStart(2, '0')}-01`;
        const startDayIndex = new Date(firstDayStr).getDay();

        // Print empty padding boxes for previous month crossover
        for (let i = 0; i < startDayIndex; i++) {
            html += '<div class="calendar_cell cell_empty"></div>';
        }

        // Draw day cells
        data.days.forEach(day => {
            const cellDate = new Date(day.date);
            let cellClass = "calendar_cell";

            if (day.status === "Available") {
                cellClass += " cell_available";

                // Highlight range selection states
                if (selectedCheckIn && isSameDate(cellDate, selectedCheckIn)) {
                    cellClass += " cell_selected_checkin";
                } else if (selectedCheckOut && isSameDate(cellDate, selectedCheckOut)) {
                    cellClass += " cell_selected_checkout";
                } else if (selectedCheckIn && selectedCheckOut && cellDate > selectedCheckIn && cellDate < selectedCheckOut) {
                    cellClass += " cell_selected_inbetween";
                }
            } else {
                cellClass += " cell_soldout";
            }

            html += `
                <div class="${cellClass}" data-date="${day.date}" data-rate="${day.rate}" data-status="${day.status}">
                    <span class="cell_date_num">${day.day}</span>
                    <span class="cell_rate">$${day.rate.toFixed(0)}</span>
                </div>
            `;
        });

        html += `</div>`;
        calendarContainer.innerHTML = html;

        // Apply interactive click event listeners to available days
        const availableCells = calendarContainer.querySelectorAll(".cell_available");
        availableCells.forEach(cell => {
            cell.addEventListener("click", () => {
                handleDateClick(cell.dataset.date);
            });
        });
    }

    function isSameDate(d1, d2) {
        return d1.getFullYear() === d2.getFullYear() &&
            d1.getMonth() === d2.getMonth() &&
            d1.getDate() === d2.getDate();
    }

    /**
     * Handles range picking clicks
     */
    function handleDateClick(dateStr) {
        const clickedDate = new Date(dateStr);

        if (!selectedCheckIn || (selectedCheckIn && selectedCheckOut)) {
            // Case 1: Start new selection
            selectedCheckIn = clickedDate;
            selectedCheckOut = null;
        } else if (selectedCheckIn && !selectedCheckOut) {
            // Case 2: User has check-in, selecting check-out
            if (clickedDate <= selectedCheckIn) {
                // If they click a date prior to check-in, reset check-in
                selectedCheckIn = clickedDate;
            } else {
                // Check if any date in-between check-in and checkout is Sold Out
                if (hasSoldOutInBetween(selectedCheckIn, clickedDate)) {
                    alert("Selected range contains sold out days. Please choose another range.");
                    selectedCheckIn = clickedDate;
                } else {
                    selectedCheckOut = clickedDate;
                }
            }
        }

        updateSidebarDetails();
        loadCalendarData(); // Refresh calendar to show highlights
    }

    /**
     * Returns true if there is a Sold Out day in the selected date span
     */
    function hasSoldOutInBetween(start, end) {
        let temp = new Date(start);
        while (temp < end) {
            const dateString = formatDateString(temp);
            // Search day data in loaded array
            const dayData = calendarDaysData.find(d => d.date === dateString);
            if (dayData && dayData.status === "Sold Out") {
                return true;
            }
            temp.setDate(temp.getDate() + 1);
        }
        return false;
    }

    function formatDateString(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    /**
     * Recalculates stay prices on sidebar inputs in real time
     */
    function updateSidebarDetails() {
        if (selectedCheckIn) {
            checkInInput.value = formatDateString(selectedCheckIn);
        } else {
            checkInInput.value = "";
        }

        if (selectedCheckOut) {
            checkOutInput.value = formatDateString(selectedCheckOut);

            // Calculate nights
            const diffTime = Math.abs(selectedCheckOut - selectedCheckIn);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            nightsDisplay.innerText = diffDays;

            // Calculate total sum dynamically
            let total = 0.0;
            let temp = new Date(selectedCheckIn);

            while (temp < selectedCheckOut) {
                const dateString = formatDateString(temp);
                const dayData = calendarDaysData.find(d => d.date === dateString);
                if (dayData) {
                    total += dayData.rate;
                }
                temp.setDate(temp.getDate() + 1);
            }

            totalDisplay.innerText = `$${total.toFixed(2)}`;
            if (sidebarBookBtn) sidebarBookBtn.disabled = false;
        } else {
            checkOutInput.value = "";
            nightsDisplay.innerText = "0";
            totalDisplay.innerText = "$0.00";
            if (sidebarBookBtn) sidebarBookBtn.disabled = true;
        }
    }
}
