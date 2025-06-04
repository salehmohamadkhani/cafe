document.addEventListener('DOMContentLoaded', function () {
    fetchDashboardMenuItems(); // Call to fetch and display menu items at the beginning

    // Event delegation for menu item cards
    const menuSection = document.getElementById('menu-section');
    if (menuSection) {
        menuSection.addEventListener('click', function (event) {
            // Find the closest menu-item-card parent element
            const menuItemCard = event.target.closest('.menu-item-card');
            if (menuItemCard) {
                const itemId = parseInt(menuItemCard.getAttribute('data-id'));
                addToOrder(itemId, menuItemCard);
            }
        });
    }

    // Handle customer search
    const customerSearch = document.getElementById('customer-search');
    if (customerSearch) {
        customerSearch.addEventListener('change', function () {
            const selectedValue = this.value;
            if (selectedValue) {
                // Parse name and phone from the selected value (format: "Name - Phone")
                const parts = selectedValue.split(' - ');
                if (parts.length === 2) {
                    document.getElementById('customer-name').value = parts[0];
                    document.getElementById('customer-phone').value = parts[1];
                }
            }
        });
    }

    // Handle discount and tax changes to update totals
    const discountInput = document.getElementById('discount');
    const taxInput = document.getElementById('tax');

    if (discountInput) {
        discountInput.addEventListener('input', updateTotals);
    }

    if (taxInput) {
        taxInput.addEventListener('input', updateTotals);
    }

    // Handle order submission
    const submitOrderBtn = document.getElementById('submit-order');
    if (submitOrderBtn) {
        submitOrderBtn.addEventListener('click', submitOrder);
    }

    // The previous initial call block has been removed as fetchDashboardMenuItems() is now called at the top.
    // Old block:
    // if (typeof fetchDashboardMenuItems === 'function') {
    //     fetchDashboardMenuItems();
    // } else {
    //     fetchAndUpdateStock();
    // }
});

// Global variables to track order items
let orderItems = [];
let totalAmount = 0;

function addToOrder(itemId, menuItemCard) {
    // Extract item details from the menu card
    const itemName = menuItemCard.querySelector('.item-name').textContent;
    const itemPriceText = menuItemCard.querySelector('.item-price').textContent;
    const itemPrice = parseInt(itemPriceText.replace(/[^\d]/g, ''));

    // Check if item already exists in the order
    const existingItemIndex = orderItems.findIndex(item => item.id === itemId);

    if (existingItemIndex !== -1) {
        // Increment quantity if item already exists
        orderItems[existingItemIndex].quantity += 1;
    } else {
        // Add new item to order
        orderItems.push({
            id: itemId,
            name: itemName,
            price: itemPrice,
            quantity: 1
        });
    }

    // Update the order display
    renderOrderItems();
    updateTotals();
}

function renderOrderItems() {
    const orderItemsList = document.getElementById('order-items-list');
    if (!orderItemsList) return;

    orderItemsList.innerHTML = '';

    if (orderItems.length === 0) {
        orderItemsList.innerHTML = '<p>هیچ آیتمی انتخاب نشده است</p>';
        return;
    }

    // Create a table for order items
    const table = document.createElement('table');
    table.className = 'order-items-table';

    // Add table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>نام</th>
            <th>قیمت</th>
            <th>تعداد</th>
            <th>جمع</th>
            <th></th>
        </tr>
    `;
    table.appendChild(thead);

    // Add table body with items
    const tbody = document.createElement('tbody');
    orderItems.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.className = 'order-item';
        tr.dataset.id = item.id;
        tr.innerHTML = `
            <td>${item.name}</td>
            <td>${item.price.toLocaleString()} تومان</td>
            <td>
                <button class="btn-quantity" data-action="decrease" data-index="${index}">-</button>
                <span class="order-qty">${item.quantity}</span>
                <button class="btn-quantity" data-action="increase" data-index="${index}">+</button>
            </td>
            <td>${(item.price * item.quantity).toLocaleString()} تومان</td>
            <td><button class="btn-remove" data-index="${index}">×</button></td>
        `;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    // Add event listeners for quantity buttons and remove buttons
    table.addEventListener('click', function (event) {
        if (event.target.classList.contains('btn-quantity')) {
            const action = event.target.getAttribute('data-action');
            const index = parseInt(event.target.getAttribute('data-index'));

            if (action === 'increase') {
                orderItems[index].quantity += 1;
            } else if (action === 'decrease') {
                if (orderItems[index].quantity > 1) {
                    orderItems[index].quantity -= 1;
                } else {
                    orderItems.splice(index, 1);
                }
            }

            renderOrderItems();
            updateTotals();
        } else if (event.target.classList.contains('btn-remove')) {
            const index = parseInt(event.target.getAttribute('data-index'));
            orderItems.splice(index, 1);
            renderOrderItems();
            updateTotals();
        }
    });

    orderItemsList.appendChild(table);
}

function updateTotals() {
    // Calculate total amount
    totalAmount = orderItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    // Get discount and tax values
    const discountEl = document.getElementById('discount');
    const taxEl = document.getElementById('tax');
    const discount = discountEl ? parseInt(discountEl.value) || 0 : 0;
    const taxPercent = taxEl ? parseInt(taxEl.value) || 0 : 0;


    // Calculate tax amount
    const taxAmount = Math.round((totalAmount - discount) * (taxPercent / 100));

    // Calculate final amount
    const finalAmount = totalAmount - discount + taxAmount;

    // Update display
    const totalAmountEl = document.getElementById('total-amount');
    const taxAmountEl = document.getElementById('tax-amount');
    const finalAmountEl = document.getElementById('final-amount');

    if (totalAmountEl) totalAmountEl.textContent = totalAmount.toLocaleString();
    if (taxAmountEl) taxAmountEl.textContent = taxAmount.toLocaleString();
    if (finalAmountEl) finalAmountEl.textContent = finalAmount.toLocaleString();
}

// Updated submitOrder function to properly send JSON data
async function submitOrder(event) {
    event.preventDefault();

    if (orderItems.length === 0) {
        alert('لطفاً حداقل یک آیتم به سفارش اضافه کنید');
        return;
    }

    const customerName = document.getElementById('customer-name').value;
    const customerPhone = document.getElementById('customer-phone').value;
    const discount = parseInt(document.getElementById('discount').value) || 0;
    const taxPercent = parseInt(document.getElementById('tax').value) || 0;

    // Prepare order data
    const orderData = {
        customer_name: customerName,
        customer_phone: customerPhone,
        items: orderItems,
        discount: discount,
        tax_percent: taxPercent
    };

    try {
        const response = await fetch('/orders/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ سفارش با موفقیت ثبت شد');
            // Reset form and order items
            const customerNameEl = document.getElementById('customer-name');
            const customerPhoneEl = document.getElementById('customer-phone');
            const customerSearchEl = document.getElementById('customer-search');
            const discountEl = document.getElementById('discount');
            const taxEl = document.getElementById('tax');

            if (customerNameEl) customerNameEl.value = '';
            if (customerPhoneEl) customerPhoneEl.value = '';
            if (customerSearchEl) customerSearchEl.value = '';
            if (discountEl) discountEl.value = '0';
            if (taxEl) taxEl.value = '12'; // Or your default tax value

            orderItems = [];
            renderOrderItems();
            updateTotals();

            // بروزرسانی موجودی آیتم‌ها در صفحه
            // This part might be redundant if fetchDashboardMenuItems is called and re-renders everything
            if (data.updatedStocks) {
                data.updatedStocks.forEach(item => {
                    const card = document.querySelector(`.menu-item-card[data-id="${item.id}"]`);
                    if (card) {
                        const stockEl = card.querySelector('.item-stock');
                        if (stockEl) {
                            stockEl.textContent = `موجودی: ${item.stock}`;
                        }
                    }
                });
            }

            // Update stock information (either by full re-render or specific update)
            if (typeof fetchDashboardMenuItems === 'function') {
                fetchDashboardMenuItems(); // Re-render the whole menu section
            } else {
                fetchAndUpdateStock(); // Or just update stocks on existing items
            }

            // باز کردن پنجره چاپ فاکتور پس از ثبت موفق
            if (data.order_id) {
                console.log(`✅ Order ${data.order_id} submitted. Opening invoice page...`);
                const printWindow = window.open(`/orders/${data.order_id}/invoice`, '_blank');
                if (!printWindow) {
                    console.warn("🛑 Failed to open print window. Check for popup blockers.");
                    alert("پنجره چاپ باز نشد. لطفاً مسدودکننده پاپ‌آپ را بررسی کنید و دوباره امتحان کنید یا به صورت دستی فاکتور را از لیست سفارشات چاپ کنید.");
                }
            }
        } else {
            alert('❌ خطا در ثبت سفارش: ' + (data.message || 'خطای نامشخص'));
        }
    } catch (error) {
        console.error('❌ خطای اتصال:', error);
        alert('❌ خطا در ارتباط با سرور');
    }
}

// Function to fetch and update stock information on existing cards (can be a fallback)
async function fetchAndUpdateStock() {
    try {
        const response = await fetch('/menu/stocks'); // Fetches only stock levels
        const data = await response.json();
        if (data.success && data.stocks) {
            data.stocks.forEach(item => {
                const card = document.querySelector(`.menu-item-card[data-id="${item.id}"]`);
                if (card) {
                    const stockEl = card.querySelector('.item-stock');
                    if (stockEl) {
                        stockEl.textContent = `موجودی: ${item.stock}`;
                    }
                }
            });
        }
    } catch (err) {
        console.error("❌ خطا در گرفتن موجودی‌ها:", err);
    }
}

// --- START: تابع جدید برای دریافت و نمایش آیتم‌های منو در داشبورد ---
async function fetchDashboardMenuItems() {
    try {
        const response = await fetch('/api/menu'); // اندپوینت جدید
        const data = await response.json();

        const container = document.getElementById('dashboard-menu-items-container');
        if (!container) {
            console.error('Container "dashboard-menu-items-container" not found.');
            return;
        }

        if (data.success && data.items && data.items.length > 0) {
            container.innerHTML = ''; // Clear previous items
            data.items.forEach(item => {
                const card = document.createElement('div');
                // menu-item-card برای سازگاری با event listener موجود در addToOrder
                // col-md-3 برای نمایش در ستون (اگر از Bootstrap استفاده می‌کنید)
                card.className = 'menu-item-card col-md-3';
                card.dataset.id = item.id;
                card.innerHTML = `
                    <div class="card-body" style="border: 1px solid #ddd; padding: 1rem; border-radius: 8px; margin: 0.5rem; background: #fff; cursor: pointer;">
                        <h5 class="item-name">${item.name}</h5>
                        <p class="item-price">${item.price.toLocaleString()} تومان</p>
                        <p class="item-stock">موجودی: ${item.stock}</p>
                    </div>
                `;
                container.appendChild(card);
            });
        } else if (data.success && data.items && data.items.length === 0) {
            container.innerHTML = '<p>هیچ آیتمی در منو برای نمایش وجود ندارد.</p>';
            console.warn("هیچ آیتمی برای منو دریافت نشد (لیست خالی).");
        } else {
            container.innerHTML = '<p>خطا در بارگذاری آیتم‌های منو.</p>';
            console.warn("پاسخ موفقیت‌آمیز نبود یا آیتم‌ها در پاسخ وجود نداشتند:", data.message || "بدون پیام");
        }
    } catch (error) {
        console.error("❌ خطا در دریافت آیتم‌های منو برای داشبورد:", error);
        const container = document.getElementById('dashboard-menu-items-container');
        if (container) {
            container.innerHTML = '<p>خطا در ارتباط با سرور برای بارگذاری آیتم‌های منو.</p>';
        }
    }
}
// --- END: تابع جدید ---