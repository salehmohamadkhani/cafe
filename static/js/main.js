document.addEventListener('DOMContentLoaded', function () {
    // JS code for cafe app will go here
    console.log("Main.js loaded");

    // حذف دکمه debugger در صورت وجود (برای رفع مشکل cache)
    function removeDebuggerButton() {
        // حذف دکمه toggle debugger
        const debugToggleBtn = document.querySelector('button[style*="position: fixed"][style*="bottom: 20px"][style*="right: 20px"][style*="z-index: 99998"]');
        if (debugToggleBtn && (debugToggleBtn.textContent.includes('🐛') || debugToggleBtn.textContent.includes('bug'))) {
            debugToggleBtn.remove();
        }
        // حذف پنل debug
        const debugPanel = document.getElementById('debug-panel');
        if (debugPanel) {
            debugPanel.remove();
        }
        // حذف هر دکمه دیگه‌ای که ممکنه debugger باشه
        document.querySelectorAll('button').forEach(btn => {
            const style = btn.getAttribute('style') || '';
            if (style.includes('z-index: 99998') || style.includes('z-index: 99999')) {
                if (btn.textContent.includes('🐛') || btn.textContent.includes('bug')) {
                    btn.remove();
                }
            }
        });
    }
    // اجرای فوری
    removeDebuggerButton();
    // اجرای مجدد بعد از یک تاخیر کوتاه (برای اطمینان)
    setTimeout(removeDebuggerButton, 100);
    setTimeout(removeDebuggerButton, 500);

    // Modal elements (assuming these exist in your HTML)
    const modal = document.getElementById('orderModal'); // Corrected ID
    const modalBody = document.getElementById('modal-body'); // Corrected ID
    // اصلاح: استفاده از getElementById برای انتخاب دکمه بستن مودال با ID 'closeModal'
    const closeBtn = document.getElementById('closeModal');

    // Close modal functionality (assuming you have a modal)
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', function () {
            modal.style.display = 'none';
            if (modalBody) {
                modalBody.innerHTML = ''; // Clear modal content on close
            }
        });
        window.addEventListener('click', function (event) {
            if (event.target == modal) {
                modal.style.display = 'none';
                if (modalBody) {
                    modalBody.innerHTML = ''; // Clear modal content on close
                }
            }
        });
    }


    document.querySelectorAll('.open-new-order').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            // Ensure modal and modalBody exist before trying to use them
            if (modal && modalBody) {
                modal.style.display = 'block';
                modalBody.innerHTML = 'در حال بارگذاری...';
                fetch('/order/new')
                    .then(res => {
                        if (!res.ok) {
                            throw new Error(`HTTP error! status: ${res.status}`);
                        }
                        return res.text();
                    })
                    .then(html => {
                        modalBody.innerHTML = html;
                        // اینجا تابع را فراخوانی می‌کنیم
                        // این فراخوانی مستقیم کار می‌کند زیرا تابع در اسکوپ سراسری تعریف شده است
                        if (typeof bindCreateOrderEvents === 'function') {
                            console.log("Calling bindCreateOrderEvents");
                            bindCreateOrderEvents();
                        } else {
                            console.error("bindCreateOrderEvents is not defined!");
                        }
                    })
                    .catch(err => {
                        console.error("Fetch error:", err);
                        modalBody.innerHTML = 'خطا در بارگذاری فرم سفارش.';
                    });
            } else {
                console.error("Modal or modalBody element not found!");
            }
        });
    });
});// اسکریپت‌های پروژه اینجا قرار می‌گیرند.
// تابع مدیریت رویدادهای فرم سفارش
function bindCreateOrderEvents() {
    console.log('bindCreateOrderEvents called');

    // بررسی وجود فرم سفارش
    const orderForm = document.getElementById('order-form');
    if (!orderForm) {
        console.log("Order form not found");
        return;
    }

    console.log("Order form found, binding events...");

    // --- جستجوی مشتری ---
    let customerSearchTimeout = null;
    const customerInput = document.getElementById('customer-search');
    const customerResults = document.getElementById('customer-results');
    if (customerInput && customerResults) {
        customerInput.addEventListener('input', function () {
            clearTimeout(customerSearchTimeout);
            const q = customerInput.value.trim();
            if (q.length < 2) {
                customerResults.innerHTML = '';
                customerResults.style.display = 'none';
                return;
            }
            customerSearchTimeout = setTimeout(() => {
                fetch(`/customer/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        customerResults.innerHTML = '';
                        if (data.length === 0) {
                            customerResults.innerHTML = '<div class="no-result">مشتری یافت نشد</div>';
                        } else {
                            data.forEach(c => {
                                const div = document.createElement('div');
                                div.className = 'customer-result';
                                div.textContent = `${c.name} (${c.phone || 'بدون شماره'})`;
                                div.addEventListener('click', function () {
                                    document.getElementById('customer-name').value = c.name;
                                    document.getElementById('customer-phone').value = c.phone || '';
                                    customerResults.innerHTML = '';
                                    customerResults.style.display = 'none';
                                });
                                customerResults.appendChild(div);
                            });
                        }
                        customerResults.style.display = 'block';
                    })
                    .catch(err => {
                        console.error("Customer search error:", err);
                        customerResults.innerHTML = '<div class="no-result">خطا در جستجو</div>';
                        customerResults.style.display = 'block';
                    });
            }, 400);
        });
        document.addEventListener('click', function (e) {
            if (!customerResults.contains(e.target) && e.target !== customerInput) {
                customerResults.style.display = 'none';
            }
        });
    }

    // --- جستجوی آیتم منو ---
    let menuSearchTimeout = null;
    const menuSearchInput = document.getElementById('menu-search');
    const menuSearchResults = document.getElementById('menu-search-results');
    let selectedMenuItem = null;
    if (menuSearchInput && menuSearchResults) {
        menuSearchInput.addEventListener('input', function () {
            clearTimeout(menuSearchTimeout);
            const q = menuSearchInput.value.trim();
            if (q.length < 2) {
                menuSearchResults.innerHTML = '';
                menuSearchResults.style.display = 'none';
                selectedMenuItem = null;
                return;
            }
            menuSearchTimeout = setTimeout(() => {
                fetch(`/menu/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        menuSearchResults.innerHTML = '';
                        if (data.length === 0) {
                            menuSearchResults.innerHTML = '<div class="no-result">آیتمی یافت نشد</div>';
                        } else {
                            data.forEach(item => {
                                const div = document.createElement('div');
                                div.className = 'menu-search-result';
                                div.textContent = `${item.name} (${item.price.toLocaleString()})`;
                                div.addEventListener('click', function () {
                                    selectedMenuItem = item;
                                    menuSearchInput.value = item.name;
                                    menuSearchResults.innerHTML = '';
                                    menuSearchResults.style.display = 'none';
                                });
                                menuSearchResults.appendChild(div);
                            });
                        }
                        menuSearchResults.style.display = 'block';
                    })
                    .catch(err => {
                        console.error("Menu search error:", err);
                        menuSearchResults.innerHTML = '<div class="no-result">خطا در جستجو</div>';
                        menuSearchResults.style.display = 'block';
                    });
            }, 400);
        });
        document.addEventListener('click', function (e) {
            if (!menuSearchResults.contains(e.target) && e.target !== menuSearchInput) {
                menuSearchResults.style.display = 'none';
            }
        });
    }

    // --- افزودن آیتم به سفارش ---
    let currentOrder = []; // Initialize currentOrder array
    function addItemToOrder(itemId, itemName, itemPrice, quantity) {
        let found = false;
        for (let i = 0; i < currentOrder.length; i++) {
            if (currentOrder[i].id == itemId) {
                currentOrder[i].quantity += quantity;
                found = true;
                break;
            }
        }
        if (!found) {
            currentOrder.push({
                id: itemId,
                name: itemName,
                price: itemPrice,
                quantity: quantity
            });
        }
        renderOrderTable();
        recalcOrder(); // Ensure recalculation happens after adding
    }

    const addMenuItemBtn = document.getElementById('add-menu-item-btn');
    if (addMenuItemBtn) {
        addMenuItemBtn.addEventListener('click', function () {
            let item = selectedMenuItem;
            let qty = parseInt(document.getElementById('menu-quantity').value, 10) || 1;
            if (!item) {
                alert('لطفاً آیتم منو را جستجو و انتخاب کنید.');
                return;
            }
            if (qty <= 0) {
                alert('تعداد باید بیشتر از صفر باشد.');
                return;
            }
            addItemToOrder(item.id, item.name, item.price, qty);
            document.getElementById('menu-search').value = '';
            document.getElementById('menu-quantity').value = 1; // Reset quantity
            selectedMenuItem = null;
        });
    }

    document.querySelectorAll('.add-to-order-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const itemId = btn.dataset.itemId;
            const itemName = btn.dataset.itemName;
            const itemPrice = parseInt(btn.dataset.itemPrice, 10);
            let quantity = parseInt(prompt(`تعداد "${itemName}" را وارد کنید:`, 1), 10);
            if (isNaN(quantity) || quantity < 1) {
                alert('تعداد نامعتبر است.');
                return;
            }
            addItemToOrder(itemId, itemName, itemPrice, quantity);
        });
    });

    // --- حذف آیتم از سفارش ---
    // Event delegation for remove buttons
    const orderItemsTableBody = document.getElementById('order-items-table')?.querySelector('tbody');
    if (orderItemsTableBody) {
        orderItemsTableBody.addEventListener('click', function (e) {
            if (e.target.classList.contains('remove-order-item')) {
                const itemId = e.target.dataset.itemId;
                currentOrder = currentOrder.filter(item => item.id != itemId);
                renderOrderTable();
                recalcOrder(); // Ensure recalculation happens after removing
            }
        });
    } else {
        console.log("Order items table tbody not found for remove listener");
    }


    // --- رندر جدول سفارش و محاسبه مبلغ ---
    function renderOrderTable() {
        const table = document.getElementById('order-items-table');
        if (!table) {
            console.log("Order items table not found");
            return;
        }

        let html = '';
        currentOrder.forEach(item => {
            const subtotal = item.price * item.quantity;
            html += `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.quantity}</td>
                    <td>${item.price.toLocaleString()}</td>
                    <td>${subtotal.toLocaleString()}</td>
                    <td><button type="button" class="btn btn-danger btn-sm remove-order-item" data-item-id="${item.id}">حذف</button></td>
                </tr>
            `;
        });
        const tbody = table.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML = html;
        } else {
            console.log("Tbody not found in order items table");
        }
        // Note: Total calculation is now handled in recalcOrder
    }

    // --- محاسبه مالیات و مبلغ نهایی ---
    function recalcOrder() {
        let total = 0;
        currentOrder.forEach(item => {
            total += item.price * item.quantity;
        });
        const discountInput = document.getElementById('order-discount');
        const taxPercentInput = document.getElementById('order-tax-percent');
        const orderTotalElement = document.getElementById('order-total'); // Element to display total before tax/discount
        const taxAmountElement = document.getElementById('order-tax-amount');
        const finalElement = document.getElementById('order-final');

        if (!discountInput || !taxPercentInput || !orderTotalElement || !taxAmountElement || !finalElement) {
            console.log("Some elements for calculation not found");
            return;
        }

        let discount = parseInt(discountInput.value, 10) || 0;
        let taxPercent = parseFloat(taxPercentInput.value) || 0;
        let tax = Math.round(total * taxPercent / 100);
        let final = total + tax - discount;

        orderTotalElement.textContent = total.toLocaleString(); // Display calculated total
        taxAmountElement.textContent = tax.toLocaleString();
        finalElement.textContent = final.toLocaleString();
    }

    // Initial calculation when the form is loaded
    recalcOrder();

    const discountInput = document.getElementById('order-discount');
    if (discountInput) {
        discountInput.addEventListener('input', recalcOrder);
    }
    const taxPercentInput = document.getElementById('order-tax-percent');
    if (taxPercentInput) {
        taxPercentInput.addEventListener('input', recalcOrder); // Also recalculate if tax percent changes
    }


    // --- ارسال سفارش به سرور ---
    orderForm.addEventListener('submit', function (e) {
        console.log("Form submit triggered");
        if (currentOrder.length === 0) {
            alert('لطفاً حداقل یک آیتم به سفارش اضافه کنید.');
            e.preventDefault();
            return false;
        }

        // آیتم‌ها را به صورت hidden input اضافه می‌کنیم
        const itemsDiv = document.getElementById('order-items-hidden');
        if (itemsDiv) {
            itemsDiv.innerHTML = ''; // Clear previous hidden inputs
            currentOrder.forEach(item => {
                let inputId = document.createElement('input');
                inputId.type = 'hidden';
                inputId.name = 'item'; // Use 'item' as name for item ID
                inputId.value = item.id;
                itemsDiv.appendChild(inputId);

                let inputQty = document.createElement('input');
                inputQty.type = 'hidden';
                inputQty.name = 'quantity'; // Use 'quantity' as name for quantity
                inputQty.value = item.quantity;
                itemsDiv.appendChild(inputQty);
            });
            console.log("Hidden inputs added for items:", currentOrder);
        } else {
            console.error("Hidden items div not found!");
            // Decide how to handle this error - maybe prevent submit?
            // e.preventDefault(); return false;
        }

        // The form will now submit normally with the added hidden inputs
        // The Flask route will read request.form.getlist('item') and request.form.getlist('quantity')
    });
}

// Make the function globally accessible (redundant in this specific structure, but added as requested)
window.bindCreateOrderEvents = bindCreateOrderEvents;