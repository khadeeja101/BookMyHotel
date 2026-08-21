document.addEventListener("DOMContentLoaded", () => {

    // Admin Multi-Tab Layout Navigation
    const tabButtons = document.querySelectorAll(".admin_tab_btn");
    const adminPanels = document.querySelectorAll(".admin_panel");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.dataset.tab; // e.g. "reports", "dateLog", "hotels", "rooms", "promotions"

            // Remove active status from all tabs and panels
            tabButtons.forEach(b => b.classList.remove("active"));
            adminPanels.forEach(p => p.classList.remove("active"));

            // Set active status on selected tab and panel
            btn.classList.add("active");

            // Format ID like "panelReports", "panelDateLog", etc.
            const formattedTabName = targetTab.charAt(0).toUpperCase() + targetTab.slice(1);
            const activePanel = document.getElementById(`panel${formattedTabName}`);
            if (activePanel) {
                activePanel.classList.add("active");
            }
        });
    });

    // Edit Hotel form loader
    const editHotelButtons = document.querySelectorAll(".edit_hotel_btn");
    const editHotelForm = document.getElementById("addHotelForm");
    const hotelFormSubmitBtn = document.getElementById("hotelFormSubmit");
    const hotelFormTitle = document.getElementById("hotelFormTitle");

    editHotelButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const data = btn.dataset;

            // If editing, change form action target url and modify title
            if (editHotelForm) {
                editHotelForm.action = `/admin/hotel/edit/${data.id}`;
                if (hotelFormTitle) hotelFormTitle.innerText = `Edit Hotel: ${data.name}`;
                if (hotelFormSubmitBtn) hotelFormSubmitBtn.innerText = "Save Changes";

                // Populate input fields
                document.getElementById("hotelNameInput").value = data.name;
                document.getElementById("hotelLocationInput").value = data.location;
                document.getElementById("hotelDescInput").value = data.desc;
                document.getElementById("hotelRatingInput").value = data.rating;
                document.getElementById("hotelSustainabilityInput").value = data.sustainability;
                document.getElementById("hotelCleanlinessInput").value = data.cleanliness;
                document.getElementById("hotelWifiInput").value = data.wifi;

                // Checkbox status
                const homeOfficeCb = document.getElementById("hotelHomeOfficeInput");
                if (homeOfficeCb) {
                    homeOfficeCb.checked = (data.homeoffice === "True");
                }

                // Jump page view to form top
                editHotelForm.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    // Reset hotel form button helper
    const resetHotelFormBtn = document.getElementById("resetHotelForm");
    if (resetHotelFormBtn) {
        resetHotelFormBtn.addEventListener("click", () => {
            if (editHotelForm) {
                editHotelForm.action = "/admin/hotel/add";
                if (hotelFormTitle) hotelFormTitle.innerText = "Add New Hotel Contract";
                if (hotelFormSubmitBtn) hotelFormSubmitBtn.innerText = "Add Hotel";
                editHotelForm.reset();
            }
        });
    }

    // Edit Promotion form loader
    const editPromoButtons = document.querySelectorAll(".edit_promo_btn");
    const editPromoForm = document.getElementById("addPromoForm");
    const promoFormSubmitBtn = document.getElementById("promoFormSubmit");
    const promoFormTitle = document.getElementById("promoFormTitle");

    editPromoButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const data = btn.dataset;
            if (editPromoForm) {
                editPromoForm.action = `/admin/promotion/edit/${data.id}`;
                if (promoFormTitle) promoFormTitle.innerText = `Edit Promotion: ${data.code}`;
                if (promoFormSubmitBtn) promoFormSubmitBtn.innerText = "Save Changes";

                // Populate input fields
                document.getElementById("promoHotelSelect").value = data.hotelId;
                document.getElementById("promoCode").value = data.code;
                document.getElementById("promoDiscount").value = data.discount;
                document.getElementById("promoStart").value = data.start;
                document.getElementById("promoEnd").value = data.end;
                document.getElementById("promoDesc").value = data.desc;

                // Jump page view to form top
                editPromoForm.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    // Reset promotion form action
    const resetPromoFormBtn = document.getElementById("resetPromoForm");
    if (resetPromoFormBtn) {
        resetPromoFormBtn.addEventListener("click", () => {
            if (editPromoForm) {
                editPromoForm.action = "/admin/promotion/add";
                if (promoFormTitle) promoFormTitle.innerText = "Create New Promotion";
                if (promoFormSubmitBtn) promoFormSubmitBtn.innerText = "Create Voucher";
                editPromoForm.reset();
            }
        });
    }

    // Edit Reservation Form Loader
    const editResButtons = document.querySelectorAll(".edit_res_btn");
    const editResCard = document.getElementById("editReservationCard");
    const editResForm = document.getElementById("editResForm");
    const editResTitle = document.getElementById("editResTitle");

    editResButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const data = btn.dataset;
            if (editResCard && editResForm) {
                editResCard.style.display = "block";
                if (editResTitle) editResTitle.innerText = `Edit Reservation #${data.id}`;
                editResForm.action = `/admin/booking/edit/${data.id}`;

                document.getElementById("editResCheckIn").value = data.checkin;
                document.getElementById("editResCheckOut").value = data.checkout;
                document.getElementById("editResAmount").value = parseFloat(data.amount).toFixed(2);
                document.getElementById("editResStatus").value = data.status;

                editResCard.scrollIntoView({ behavior: "smooth" });
            }
        });
    });
});
