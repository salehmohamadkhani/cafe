let currentTableId = null;
let currentTableNumber = null;
let tableItems = [];

// باز کردن پاپ‌آپ میز
function openTableModal(tableId, tableNumber) {
    console.log('openTableModal called with:', tableId, tableNumber);
    currentTableId = tableId;
    currentTableNumber = tableNumber;
    isNewCustomer = false; // ریست کردن وضعیت مشتری جدید
    
    const modal = document.getElementById('table-modal');
    if (!modal) {
        console.error('Table modal not found!');
        alert('خطا: مدال میز یافت نشد');
        return;
    }
    
    const modalNumberEl = document.getElementById('table-modal-number');
    if (modalNumberEl) {
        modalNumberEl.textContent = tableNumber;
    }
    
    modal.style.display = 'flex';
    console.log('Modal display set to flex');
    
    loadTableData(tableId);
    
    // تنظیم event listener برای دکمه‌های ثبت و تسویه (باید هر بار که modal باز می‌شود تنظیم شود)
    setTimeout(() => {
        const submitBtn = document.getElementById('submit-table-order');
        const checkoutBtn = document.getElementById('checkout-table');
        
        // حذف event listener های قبلی و اضافه کردن جدید
        if (submitBtn) {
            // حذف تمام event listener های قبلی
            const newSubmitBtn = submitBtn.cloneNode(true);
            submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);
            
            // اضافه کردن event listener جدید
            newSubmitBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('Submit button clicked!');
                submitTableOrder();
                return false;
            }, true); // استفاده از capture phase
        }
        
        if (checkoutBtn) {
            // حذف تمام event listener های قبلی
            const newCheckoutBtn = checkoutBtn.cloneNode(true);
            checkoutBtn.parentNode.replaceChild(newCheckoutBtn, checkoutBtn);
            
            // اضافه کردن event listener جدید
            newCheckoutBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('Checkout button clicked!');
                checkoutTable();
                return false;
            }, true); // استفاده از capture phase
        }
    }, 200);
    
    // تنظیم event listener مستقیم روی آیتم‌های منو
    setTimeout(() => {
        const menuItems = modal.querySelectorAll('.menu-item-selectable');
        menuItems.forEach(item => {
            // اگر event listener قبلی وجود دارد، آن را حذف نکنیم
            // فقط event listener جدید اضافه می‌کنیم
            item.addEventListener('click', function(e) {
                e.stopPropagation(); // جلوگیری از انتشار event به modal
                e.preventDefault(); // جلوگیری از رفتار پیش‌فرض
                const itemId = parseInt(item.getAttribute('data-item-id'));
                if (itemId && !isNaN(itemId) && currentTableId) {
                    console.log('Adding item to table (direct):', itemId);
                    addItemToTable(itemId);
                }
            }, true); // استفاده از capture phase
        });
        
        // جلوگیری از بسته شدن modal وقتی روی محتوای آن کلیک می‌شود
        const modalContent = modal.querySelector('.table-modal-content');
        if (modalContent) {
            // حذف event listener قبلی اگر وجود دارد
            const newModalContent = modalContent.cloneNode(true);
            modalContent.parentNode.replaceChild(newModalContent, modalContent);
            
            newModalContent.addEventListener('click', function(e) {
                // اگر روی دکمه‌ها یا آیتم منو کلیک شده، event را متوقف نکن
                if (e.target.closest('.menu-item-selectable') || 
                    e.target.closest('#submit-table-order') || 
                    e.target.closest('#checkout-table') ||
                    e.target.id === 'submit-table-order' ||
                    e.target.id === 'checkout-table') {
                    return; // اجازه بده event به دکمه برسد
                }
                // در غیر این صورت، event را متوقف کن
                e.stopPropagation();
            }, false);
        }
    }, 100);
    
    // راه‌اندازی مجدد جستجوی مشتری بعد از باز شدن modal
    setTimeout(() => {
        initTableCustomerSearch();
    }, 100);
}

// بستن پاپ‌آپ میز
async function closeTableModal() {
    const tableIdToUpdate = currentTableId; // ذخیره tableId قبل از پاک کردن
    document.getElementById('table-modal').style.display = 'none';
    currentTableId = null;
    currentTableNumber = null;
    tableItems = [];
    clearTableForm();
    
    // به‌روزرسانی کارت میز بعد از بستن modal
    if (tableIdToUpdate) {
        await updateTableCard(tableIdToUpdate);
    }
}

// بارگذاری اطلاعات میز
let currentTableData = null; // ذخیره داده‌های میز برای استفاده در updateTableTotals

async function loadTableData(tableId) {
    try {
        const response = await fetch(`/table/${tableId}`);
        const data = await response.json();
        
        // ذخیره داده‌های میز
        currentTableData = data;
        
        // پر کردن فرم
        document.getElementById('table-customer-name').value = data.customer_name || '';
        document.getElementById('table-customer-phone').value = data.customer_phone || '';
        
        // پر کردن فیلدهای تخفیف - فقط اگر فیلدها خالی هستند یا مقدار آنها 0 است
        const discountAmount = data.discount_amount || 0;
        const discountPercent = data.discount_percent || 0;
        const discountAmountInput = document.getElementById('table-discount-amount');
        const discountPercentInput = document.getElementById('table-discount-percent');
        
        // فقط اگر فیلد خالی است یا 0 است، مقدار را از سرور بگیر
        if (discountAmountInput && (!discountAmountInput.value || discountAmountInput.value === '0')) {
            discountAmountInput.value = discountAmount;
        }
        if (discountPercentInput && (!discountPercentInput.value || discountPercentInput.value === '0')) {
            discountPercentInput.value = discountPercent;
        }
        
        // اگر تخفیف قبلاً اعمال شده، دکمه‌ها را غیرفعال کن
        const applyDiscountAmountBtn = document.getElementById('apply-table-discount-amount');
        const applyDiscountPercentBtn = document.getElementById('apply-table-discount-percent');
        
        if (applyDiscountAmountBtn) {
            if (discountAmount > 0) {
                applyDiscountAmountBtn.disabled = true;
                applyDiscountAmountBtn.style.opacity = '0.5';
                applyDiscountAmountBtn.style.cursor = 'not-allowed';
                applyDiscountAmountBtn.title = 'تخفیف اعمال شده است';
                applyDiscountAmountBtn.textContent = '✓';
                applyDiscountAmountBtn.style.background = 'var(--color-success)';
            } else {
                applyDiscountAmountBtn.disabled = false;
                applyDiscountAmountBtn.style.opacity = '1';
                applyDiscountAmountBtn.style.cursor = 'pointer';
                applyDiscountAmountBtn.title = 'اعمال تخفیف عددی';
                applyDiscountAmountBtn.textContent = '✓';
                applyDiscountAmountBtn.style.background = '';
            }
        }
        
        if (applyDiscountPercentBtn) {
            if (discountPercent > 0) {
                applyDiscountPercentBtn.disabled = true;
                applyDiscountPercentBtn.style.opacity = '0.5';
                applyDiscountPercentBtn.style.cursor = 'not-allowed';
                applyDiscountPercentBtn.title = 'تخفیف اعمال شده است';
                applyDiscountPercentBtn.textContent = '✓';
                applyDiscountPercentBtn.style.background = 'var(--color-success)';
            } else {
                applyDiscountPercentBtn.disabled = false;
                applyDiscountPercentBtn.style.opacity = '1';
                applyDiscountPercentBtn.style.cursor = 'pointer';
                applyDiscountPercentBtn.title = 'اعمال تخفیف درصدی';
                applyDiscountPercentBtn.textContent = '✓';
                applyDiscountPercentBtn.style.background = '';
            }
        }
        
        // ذخیره order_id و وضعیت سفارش برای نمایش دکمه تسویه
        currentTableOrderId = data.order_id || null;
        currentTableOrderStatus = data.order_status || null;
        console.log('Order ID برای میز:', currentTableOrderId, 'Status:', currentTableOrderStatus);
        
        // تغییر متن دکمه "ثبت میز" به "اصلاح سفارش" اگر سفارش ثبت شده باشد
        const submitBtn = document.getElementById('submit-table-order');
        if (submitBtn) {
            if (currentTableOrderId && currentTableOrderStatus && currentTableOrderStatus !== 'پرداخت شده') {
                submitBtn.textContent = 'اصلاح سفارش';
                submitBtn.title = 'به‌روزرسانی سفارش موجود';
            } else {
                submitBtn.textContent = 'ثبت میز';
                submitBtn.title = 'ثبت سفارش جدید';
            }
        }
        
        // نمایش آیتم‌ها
        tableItems = data.items || [];
        renderTableItems();
        
        // به‌روزرسانی محاسبات با استفاده از داده‌های بارگذاری شده
        updateTableTotals();
    } catch (error) {
        console.error('خطا در بارگذاری اطلاعات میز:', error);
        alert('خطا در بارگذاری اطلاعات میز');
    }
}

// نمایش آیتم‌های میز
let currentTableOrderId = null;
let currentTableOrderStatus = null;

function renderTableItems() {
    const container = document.getElementById('table-items-list');
    container.innerHTML = '';
    
    if (tableItems.length === 0) {
        container.innerHTML = '<p class="empty-message">هیچ آیتمی انتخاب نشده است</p>';
        return;
    }
    
    console.log('رندر کردن آیتم‌ها، order_id:', currentTableOrderId);
    
    // ساخت جدول
    const table = document.createElement('table');
    
    // ساخت هدر جدول
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>نام آیتم</th>
            <th>قیمت واحد</th>
            <th>عملیات</th>
            <th>جمع کل</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // ساخت بدنه جدول
    const tbody = document.createElement('tbody');
    tableItems.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-item-id', item.id);
        tr.innerHTML = `
            <td>${item.menu_item_name}</td>
            <td>${item.unit_price.toLocaleString()}</td>
            <td class="qty-controls-cell">
                <div class="qty-controls">
                    <button type="button" onclick="decreaseItemQuantity(${item.id})" class="btn-quantity decrease-qty">-</button>
                    <span class="order-qty">${item.quantity}</span>
                    <button type="button" onclick="increaseItemQuantity(${item.id})" class="btn-quantity increase-qty">+</button>
                    <button type="button" onclick="showRemoveReasonField(${item.id})" class="btn-remove remove-item">×</button>
                </div>
            </td>
            <td>${item.total_price.toLocaleString()}</td>
        `;
        tbody.appendChild(tr);
        
        // اضافه کردن row برای فیلد دلیل حذف (مخفی)
        const reasonRow = document.createElement('tr');
        reasonRow.className = 'removal-reason-row';
        reasonRow.setAttribute('data-item-id', item.id);
        reasonRow.style.display = 'none';
        reasonRow.innerHTML = `
            <td colspan="4" style="padding: 1rem; background-color: #fff3cd; border-top: 2px solid #ffc107;">
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <label style="font-weight: 600; color: #856404;">دلیل حذف:</label>
                    <input type="text" id="removal-reason-${item.id}" class="removal-reason-input" 
                           placeholder="لطفاً دلیل حذف این آیتم را وارد کنید..." 
                           style="flex: 1; padding: 0.5rem; border: 1px solid #ffc107; border-radius: 4px;">
                    <button type="button" onclick="confirmRemoveTableItem(${item.id})" 
                            class="btn btn-primary" style="padding: 0.5rem 1rem;">تأیید حذف</button>
                    <button type="button" onclick="hideRemoveReasonField(${item.id})" 
                            class="btn btn-secondary" style="padding: 0.5rem 1rem;">لغو</button>
                </div>
            </td>
        `;
        tbody.appendChild(reasonRow);
    });
    table.appendChild(tbody);
    
    container.appendChild(table);
}

// افزودن آیتم به میز
async function addItemToTable(menuItemId) {
    if (!currentTableId) {
        console.error('currentTableId is null');
        alert('لطفاً ابتدا یک میز را انتخاب کنید');
        return;
    }
    
    if (!menuItemId || isNaN(menuItemId)) {
        console.error('Invalid menuItemId:', menuItemId);
        return;
    }
    
    console.log('Adding item to table:', currentTableId, 'item:', menuItemId);
    
    try {
        const response = await fetch(`/table/${currentTableId}/add_item`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                menu_item_id: menuItemId,
                quantity: 1
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('HTTP error:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            console.log('Item added successfully');
            await loadTableData(currentTableId);
            updateTableCard(currentTableId);
        } else {
            console.error('Server error:', data.message);
            alert(data.message || 'خطا در افزودن آیتم');
        }
    } catch (error) {
        console.error('خطا در افزودن آیتم:', error);
        alert('خطا در افزودن آیتم به میز: ' + error.message);
    }
}

// نمایش فیلد دلیل حذف
function showRemoveReasonField(itemId) {
    // همیشه دلیل بپرسیم
    const reasonRow = document.querySelector(`tr.removal-reason-row[data-item-id="${itemId}"]`);
    if (reasonRow) {
        reasonRow.style.display = 'table-row';
        const input = reasonRow.querySelector('.removal-reason-input');
        if (input) {
            input.focus();
        }
    } else {
        // اگر row وجود ندارد، مستقیماً حذف کنیم (باید row در renderTableItems ساخته شود)
        console.warn('Removal reason row not found for item:', itemId);
        // اگر row وجود ندارد، مستقیماً حذف کن
        removeTableItemDirectly(itemId);
    }
}

// مخفی کردن فیلد دلیل حذف
function hideRemoveReasonField(itemId) {
    const reasonRow = document.querySelector(`tr.removal-reason-row[data-item-id="${itemId}"]`);
    if (reasonRow) {
        reasonRow.style.display = 'none';
        const input = reasonRow.querySelector('.removal-reason-input');
        if (input) {
            input.value = '';
        }
    }
}

// تأیید حذف با دلیل
async function confirmRemoveTableItem(itemId) {
    if (!currentTableId) return;
    
    const input = document.getElementById(`removal-reason-${itemId}`);
    const removalReason = input ? input.value.trim() : '';
    
    if (!removalReason) {
        alert('لطفاً دلیل حذف را وارد کنید');
        input.focus();
        return;
    }
    
    try {
        const response = await fetch(`/table/${currentTableId}/remove_item/${itemId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ removal_reason: removalReason })
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTableData(currentTableId);
            updateTableCard(currentTableId);
        } else {
            alert(data.message || 'خطا در حذف آیتم');
        }
    } catch (error) {
        console.error('خطا در حذف آیتم:', error);
        alert('خطا در حذف آیتم از میز');
    }
}

// حذف مستقیم آیتم از میز (بدون بررسی دلیل)
async function removeTableItemDirectly(itemId) {
    if (!currentTableId) return;
    
    try {
        const response = await fetch(`/table/${currentTableId}/remove_item/${itemId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTableData(currentTableId);
            updateTableCard(currentTableId);
        } else {
            // اگر نیاز به دلیل بود، فیلد را نمایش بده
            if (data.requires_reason) {
                showRemoveReasonField(itemId);
            } else {
                alert(data.message || 'خطا در حذف آیتم');
            }
        }
    } catch (error) {
        console.error('خطا در حذف آیتم:', error);
        alert('خطا در حذف آیتم از میز');
    }
}

// حذف آیتم از میز - همیشه دلیل می‌پرسیم
async function removeTableItem(itemId) {
    if (!currentTableId) return;
    
    // همیشه دلیل بپرسیم (حتی اگر سفارش ثبت نشده باشد)
    showRemoveReasonField(itemId);
}

// افزایش تعداد آیتم
async function increaseItemQuantity(itemId) {
    const item = tableItems.find(i => i.id === itemId);
    if (!item) return;
    
    await updateItemQuantity(itemId, item.quantity + 1);
}

// کاهش تعداد آیتم
async function decreaseItemQuantity(itemId) {
    const item = tableItems.find(i => i.id === itemId);
    if (!item) return;
    
    if (item.quantity > 1) {
        await updateItemQuantity(itemId, item.quantity - 1);
    } else {
        await removeTableItem(itemId);
    }
}

// به‌روزرسانی تعداد آیتم
async function updateItemQuantity(itemId, quantity) {
    if (!currentTableId) return;
    
    try {
        const response = await fetch(`/table/${currentTableId}/update_item/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity })
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTableData(currentTableId);
            updateTableCard(currentTableId);
        } else {
            alert(data.message || 'خطا در به‌روزرسانی تعداد');
        }
    } catch (error) {
        console.error('خطا در به‌روزرسانی تعداد:', error);
        alert('خطا در به‌روزرسانی تعداد آیتم');
    }
}

// به‌روزرسانی اطلاعات مشتری
async function updateTableCustomer() {
    if (!currentTableId) return Promise.resolve();
    
    const customerName = document.getElementById('table-customer-name').value;
    const customerPhone = document.getElementById('table-customer-phone').value;
    const birthDateInput = document.getElementById('table-customer-birth-date');
    const birthDate = birthDateInput && birthDateInput.value ? birthDateInput.value : null;
    const discountAmount = parseInt(document.getElementById('table-discount-amount').value) || 0;
    const discountPercent = parseFloat(document.getElementById('table-discount-percent').value) || 0;
    
    // محاسبه مجموع تخفیف برای backward compatibility
    const total = tableItems.reduce((sum, item) => sum + item.total_price, 0);
    const discountFromPercent = Math.floor(total * discountPercent / 100);
    const totalDiscount = discountAmount + discountFromPercent;
    
    try {
        const response = await fetch(`/table/${currentTableId}/update_customer`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: customerName,
                customer_phone: customerPhone,
                birth_date: birthDate,
                discount: totalDiscount,
                discount_amount: discountAmount,
                discount_percent: discountPercent
            })
        });
        
        const data = await response.json();
        if (data.success) {
            // به‌روزرسانی محاسبات محلی
            updateTableTotals();
            
            // به‌روزرسانی currentTableData با مقادیر جدید
            if (currentTableData) {
                currentTableData.customer_name = customerName;
                currentTableData.customer_phone = customerPhone;
                currentTableData.discount = totalDiscount;
                currentTableData.discount_amount = discountAmount;
                currentTableData.discount_percent = discountPercent;
            }
            
            // فقط کارت را به‌روزرسانی کن، بدون reload کامل داده‌ها (تا تخفیف حفظ شود)
            // updateTableCard را صدا نزنیم چون باعث reset شدن تخفیف می‌شود
            // updateTableCard(currentTableId);
            return Promise.resolve();
        } else {
            alert(data.message || 'خطا در به‌روزرسانی اطلاعات');
            return Promise.reject(new Error(data.message || 'خطا در به‌روزرسانی اطلاعات'));
        }
    } catch (error) {
        console.error('خطا در به‌روزرسانی اطلاعات:', error);
        alert('خطا در به‌روزرسانی اطلاعات مشتری');
        return Promise.reject(error);
    }
}

// ثبت سفارش میز
async function submitTableOrder() {
    if (!currentTableId) {
        console.error('currentTableId is null');
        alert('لطفاً ابتدا یک میز را انتخاب کنید');
        return;
    }
    
    // اگر سفارش ثبت شده باشد، نیازی به بررسی tableItems نیست
    // چون آیتم‌ها در OrderItem هستند
    if (!currentTableOrderId) {
        // بررسی اینکه آیا آیتمی در میز وجود دارد (فقط برای سفارش جدید)
        if (!tableItems || tableItems.length === 0) {
            alert('لطفاً حداقل یک آیتم انتخاب کنید');
            return;
        }
    }
    
    try {
        console.log('Submitting table order for table:', currentTableId);
        const birthDateInput = document.getElementById('table-customer-birth-date');
        const birthDate = birthDateInput && birthDateInput.value ? birthDateInput.value : null;
        
        const response = await fetch(`/table/${currentTableId}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                birth_date: birthDate
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            // بستن modal فوراً
            closeTableModal();
            if (currentTableOrderId) {
                alert(`سفارش با شماره فاکتور ${data.invoice_number} با موفقیت به‌روزرسانی شد`);
            } else {
                alert(`سفارش با شماره فاکتور ${data.invoice_number} با موفقیت ثبت شد`);
            }
            // به‌روزرسانی صفحه برای نمایش تغییرات
            location.reload();
        } else {
            alert(data.message || 'خطا در ثبت سفارش');
        }
    } catch (error) {
        console.error('خطا در ثبت سفارش:', error);
        alert('خطا در ثبت سفارش میز: ' + error.message);
    }
}

// تسویه میز (از داخل modal)
async function checkoutTable() {
    if (!currentTableId) {
        console.error('currentTableId is null');
        alert('لطفاً ابتدا یک میز را انتخاب کنید');
        return;
    }
    
    try {
        console.log('Checking out table:', currentTableId);
        const response = await fetch(`/table/${currentTableId}/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                payment_method: 'کارتخوان'
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Checkout response:', data);
        
        if (data.success) {
            alert(`میز با موفقیت تسویه شد. شماره فاکتور: ${data.invoice_number}`);
            closeTableModal();
            // به‌روزرسانی صفحه برای نمایش تغییرات
            location.reload();
        } else {
            alert(data.message || 'خطا در تسویه میز');
        }
    } catch (error) {
        console.error('خطا در تسویه میز:', error);
        alert('خطا در تسویه میز: ' + error.message);
    }
}

// به‌روزرسانی مبلغ کل میز
// این تابع از مقادیر سرور استفاده می‌کند (از currentTableData)
function updateTableTotals() {
    try {
        // همیشه از tableItems محاسبه می‌کنیم تا تخفیف لحاظ شود
        const total = tableItems.reduce((sum, item) => sum + item.total_price, 0);
        
        // محاسبه تخفیف درصدی (ابتدا)
        const discountPercentEl = document.getElementById('table-discount-percent');
        const discountAmountEl = document.getElementById('table-discount-amount');
        
        if (!discountPercentEl || !discountAmountEl) {
            if (window.debug) window.debug.warn('Table Totals', 'Discount input elements not found');
            return;
        }
        
        const discountPercent = parseFloat(discountPercentEl.value) || 0;
        const discountFromPercent = Math.floor(total * discountPercent / 100);
        
        // محاسبه تخفیف عددی (بعد از درصدی)
        const discountAmount = parseInt(discountAmountEl.value) || 0;
        
        // مجموع تخفیف‌ها
        const totalDiscount = discountFromPercent + discountAmount;
        
        if (window.debug) {
            window.debug.log('Table Totals', 'Calculating totals', {
                total,
                discountPercent,
                discountFromPercent,
                discountAmount,
                totalDiscount
            });
        }
        
        const taxPercent = Number(window.CAFE_TAX_PERCENT ?? 9);
        const tax = Math.floor((total - totalDiscount) * taxPercent / 100);
        const final = total - totalDiscount + tax;
        
        const totalAmountEl = document.getElementById('table-total-amount');
        const taxAmountEl = document.getElementById('table-tax-amount');
        const finalAmountEl = document.getElementById('table-final-amount');
        
        if (!totalAmountEl || !taxAmountEl || !finalAmountEl) {
            if (window.debug) window.debug.error('Table Totals', 'Summary elements not found');
            return;
        }
        
        totalAmountEl.textContent = total.toLocaleString();
        taxAmountEl.textContent = tax.toLocaleString();
        finalAmountEl.textContent = final.toLocaleString();
        
        // نمایش تخفیف در summary
        const discountRow = document.getElementById('table-discount-row');
        const discountDisplay = document.getElementById('table-discount-display');
        
        if (!discountRow || !discountDisplay) {
            if (window.debug) window.debug.warn('Table Totals', 'Discount display elements not found');
            return;
        }
        
        if (totalDiscount > 0) {
            // ساخت متن تخفیف
            let discountText = '';
            if (discountPercent > 0 && discountAmount > 0) {
                // هر دو نوع تخفیف
                discountText = `${discountPercent}% (${discountFromPercent.toLocaleString()}) + ${discountAmount.toLocaleString()} = ${totalDiscount.toLocaleString()}`;
            } else if (discountPercent > 0) {
                // فقط درصدی
                discountText = `${discountPercent}% (${discountFromPercent.toLocaleString()})`;
            } else if (discountAmount > 0) {
                // فقط عددی
                discountText = `${discountAmount.toLocaleString()}`;
            }
            discountDisplay.textContent = discountText;
            discountRow.style.display = 'flex';
            
            if (window.debug) {
                window.debug.success('Table Totals', 'Discount displayed', { discountText, totalDiscount });
            }
        } else {
            discountRow.style.display = 'none';
        }
    
        // به‌روزرسانی currentTableData برای استفاده در جاهای دیگر
        if (currentTableData) {
            currentTableData.total_amount = total;
            currentTableData.tax_amount = tax;
            currentTableData.final_amount = final;
            currentTableData.discount = totalDiscount;
            currentTableData.discount_amount = discountAmount;
            currentTableData.discount_percent = discountPercent;
        }
    } catch (error) {
        if (window.debug) {
            window.debug.error('Table Totals', 'Error in updateTableTotals', {
                error: error.message,
                stack: error.stack
            });
        }
        console.error('Error in updateTableTotals:', error);
    }
}

// به‌روزرسانی کارت میز
async function updateTableCard(tableId) {
    try {
        const response = await fetch(`/table/${tableId}`);
        if (!response.ok) {
            console.error('خطا در دریافت اطلاعات میز');
            return;
        }
        
        const data = await response.json();
        
        const tableCard = document.querySelector(`[data-table-id="${tableId}"]`);
        if (!tableCard) {
            console.log('کارت میز یافت نشد:', tableId);
            return;
        }
        
        // به‌روزرسانی badge وضعیت
        const badge = tableCard.querySelector('.table-card__badge');
        if (badge) {
            badge.textContent = data.status || 'خالی';
            badge.className = `table-card__badge ${data.status === 'اشغال شده' ? 'occupied' : 'empty'}`;
        }
        
        // به‌روزرسانی بخش مشتری و مبلغ
        const customerSection = tableCard.querySelector('.table-card__customer');
        const emptySection = tableCard.querySelector('.table-card__empty');
        const orderSection = tableCard.querySelector('.table-card__order');
        const actionsSection = tableCard.querySelector('.table-card__actions');
        
        if (data.status === 'اشغال شده' && (data.items && data.items.length > 0)) {
            // اگر میز اشغال شده و آیتم دارد
            if (emptySection) {
                emptySection.remove();
            }
            
            if (!customerSection) {
                // ساخت بخش مشتری اگر وجود ندارد
                const newCustomerSection = document.createElement('div');
                newCustomerSection.className = 'table-card__customer';
                newCustomerSection.innerHTML = `
                    <div>
                        <span>مشتری</span>
                        <strong>${data.customer_name || 'بدون نام'}</strong>
                    </div>
                    <div>
                        <span>مبلغ با تخفیف</span>
                        <strong>${(data.final_amount || 0).toLocaleString('fa-IR')}</strong>
                    </div>
                `;
                // قرار دادن قبل از بخش order یا actions
                const insertBefore = orderSection || actionsSection || emptySection;
                if (insertBefore) {
                    tableCard.insertBefore(newCustomerSection, insertBefore);
                } else {
                    tableCard.appendChild(newCustomerSection);
                }
            } else {
                // به‌روزرسانی بخش مشتری موجود
                const customerName = customerSection.querySelector('strong');
                const amount = customerSection.querySelectorAll('strong')[1];
                if (customerName) {
                    customerName.textContent = data.customer_name || 'بدون نام';
                }
                if (amount) {
                    amount.textContent = `${(data.final_amount || 0).toLocaleString('fa-IR')}`;
                }
            }
        } else {
            // اگر میز خالی است
            if (customerSection) {
                customerSection.remove();
            }
            if (orderSection) {
                orderSection.remove();
            }
            if (actionsSection) {
                actionsSection.remove();
            }
            
            if (!emptySection) {
                const newEmptySection = document.createElement('div');
                newEmptySection.className = 'table-card__empty';
                newEmptySection.textContent = 'میز آماده پذیرش';
                tableCard.appendChild(newEmptySection);
            }
        }
        
        console.log('کارت میز به‌روزرسانی شد:', tableId, data.status);
    } catch (error) {
        console.error('خطا در به‌روزرسانی کارت میز:', error);
    }
}

// پاک کردن فرم
function clearTableForm() {
    document.getElementById('table-customer-name').value = '';
    document.getElementById('table-customer-phone').value = '';
    document.getElementById('table-discount').value = '0';
    document.getElementById('table-items-list').innerHTML = '<p class="empty-message">هیچ آیتمی انتخاب نشده است</p>';
    
    // فعال کردن دکمه اعمال تخفیف
    const applyDiscountBtn = document.getElementById('apply-table-discount');
    if (applyDiscountBtn) {
        applyDiscountBtn.disabled = false;
        applyDiscountBtn.style.opacity = '1';
        applyDiscountBtn.style.cursor = 'pointer';
        applyDiscountBtn.title = 'اعمال تخفیف';
        applyDiscountBtn.textContent = '✓';
        applyDiscountBtn.style.background = '';
    }
    
    updateTableTotals();
}

// فیلتر کردن آیتم‌های منو
function filterMenuItems() {
    const searchTerm = document.getElementById('menu-search-input').value.toLowerCase();
    const menuItems = document.querySelectorAll('#table-modal .menu-item-selectable');
    const menuCategories = document.querySelectorAll('#table-modal .menu-category');
    
    // فیلتر کردن آیتم‌ها
    menuItems.forEach(item => {
        const itemName = item.getAttribute('data-item-name').toLowerCase();
        if (searchTerm === '' || itemName.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
    
    // نمایش یا مخفی کردن دسته‌بندی‌ها بر اساس آیتم‌های قابل مشاهده
    menuCategories.forEach(category => {
        if (searchTerm === '') {
            // اگر جستجو خالی است، همه دسته‌بندی‌ها را نمایش بده
            category.style.display = 'block';
        } else {
            // بررسی اینکه آیا حداقل یک آیتم قابل مشاهده در این دسته‌بندی وجود دارد
            const itemsInCategory = category.querySelectorAll('.menu-item-selectable');
            let hasVisibleItem = false;
            itemsInCategory.forEach(item => {
                if (item.style.display !== 'none') {
                    hasVisibleItem = true;
                }
            });
            category.style.display = hasVisibleItem ? 'block' : 'none';
        }
    });
}

// کپی کردن فاکتور
async function copyInvoice(orderId) {
    try {
        // دریافت اطلاعات فاکتور از API
        const response = await fetch(`/order/orders/${orderId}/invoice`, {
            headers: {
                'Accept': 'text/html'
            }
        });
        if (!response.ok) {
            throw new Error('خطا در دریافت فاکتور');
        }
        
        const htmlContent = await response.text();
        
        // ایجاد یک div موقت برای استخراج متن
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;
        
        // استخراج متن از فاکتور
        const invoiceBox = tempDiv.querySelector('.invoice-box');
        if (!invoiceBox) {
            throw new Error('ساختار فاکتور یافت نشد');
        }
        
        // ساخت متن فاکتور
        let invoiceText = '';
        
        // هدر
        const header = invoiceBox.querySelector('.header');
        if (header) {
            const headerLines = header.innerText.trim().split('\n');
            headerLines.forEach(line => {
                if (line.trim()) {
                    invoiceText += line.trim() + '\n';
                }
            });
            invoiceText += '\n';
        }
        
        // جدول آیتم‌ها
        const table = invoiceBox.querySelector('table');
        if (table) {
            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td, th');
                if (cells.length > 0) {
                    const rowText = Array.from(cells).map(cell => {
                        const text = cell.innerText.trim();
                        return text || '-';
                    }).join(' | ');
                    invoiceText += rowText + '\n';
                }
            });
            invoiceText += '\n';
        }
        
        // جمع‌ها
        const totalsSection = invoiceBox.querySelector('.totals-section');
        if (totalsSection) {
            const totalsLines = totalsSection.innerText.trim().split('\n');
            totalsLines.forEach(line => {
                if (line.trim()) {
                    invoiceText += line.trim() + '\n';
                }
            });
        }
        
        // فوتر
        const footer = invoiceBox.querySelector('.footer');
        if (footer) {
            invoiceText += '\n' + footer.innerText.trim();
        }
        
        // کپی به clipboard
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(invoiceText);
            alert('✅ فاکتور با موفقیت کپی شد!');
        } else {
            // Fallback برای مرورگرهای قدیمی
            const textArea = document.createElement('textarea');
            textArea.value = invoiceText;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            alert('✅ فاکتور با موفقیت کپی شد!');
        }
        
    } catch (error) {
        console.error('خطا در کپی فاکتور:', error);
        alert('❌ خطا در کپی فاکتور: ' + error.message);
    }
}

// تسویه میز از داشبورد
// کپی فاکتور میز به clipboard بدون باز کردن صفحه
async function printTableInvoice(orderId, event) {
    if (event) {
        event.stopPropagation(); // جلوگیری از باز شدن modal
        event.preventDefault(); // جلوگیری از رفتار پیش‌فرض
    }
    
    try {
        console.log('📋 Fetching invoice text for order:', orderId);
        // دریافت محتوای فاکتور به صورت متن
        const response = await fetch(`/orders/${orderId}/invoice/text`);
        
        if (!response.ok) {
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.text) {
            // کپی کردن به clipboard
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(data.text);
                alert('✅ فاکتور با موفقیت کپی شد!');
            } else {
                // Fallback برای مرورگرهای قدیمی
                const textArea = document.createElement('textarea');
                textArea.value = data.text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {
                    document.execCommand('copy');
                    alert('✅ فاکتور با موفقیت کپی شد!');
                } catch (err) {
                    console.error('❌ خطا در کپی:', err);
                    alert('خطا در کپی فاکتور. لطفاً محتوا را دستی کپی کنید:\n\n' + data.text);
                }
                
                document.body.removeChild(textArea);
            }
        } else {
            throw new Error('خطا در دریافت محتوای فاکتور');
        }
    } catch (error) {
        console.error('❌ خطا در کپی فاکتور:', error);
        alert('❌ خطا در کپی فاکتور: ' + error.message);
    }
}

function toggleCheckoutOptions(tableId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const target = document.getElementById(`checkout-options-${tableId}`);
    if (!target) return;
    const isActive = target.classList.contains('active');
    document.querySelectorAll('.table-card__checkout-options').forEach(opt => opt.classList.remove('active'));
    if (!isActive) {
        target.classList.add('active');
    }
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('.table-card__checkout')) {
        document.querySelectorAll('.table-card__checkout-options').forEach(opt => opt.classList.remove('active'));
    }
});

async function settleTableFromDashboard(tableId, event, paymentMethod = 'کارتخوان') {
    if (event) {
        event.stopPropagation(); // جلوگیری از باز شدن modal
        event.preventDefault(); // جلوگیری از رفتار پیش‌فرض
    }
    
    try {
        const response = await fetch(`/table/${tableId}/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                payment_method: paymentMethod
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            // بستن dropdown
            document.querySelectorAll('.table-card__checkout-options').forEach(opt => opt.classList.remove('active'));
            
            // پیدا کردن کارت میز و به‌روزرسانی آن
            const tableCard = document.querySelector(`.table-card[data-table-id="${tableId}"]`);
            if (tableCard) {
                // تغییر وضعیت میز به خالی
                const badge = tableCard.querySelector('.table-card__badge');
                if (badge) {
                    badge.textContent = 'خالی';
                    badge.classList.remove('occupied');
                    badge.classList.add('empty');
                }
                
                // حذف تمام بخش‌های مربوط به سفارش
                const customerSection = tableCard.querySelector('.table-card__customer');
                const orderSections = tableCard.querySelectorAll('.table-card__order');
                const actionsSection = tableCard.querySelector('.table-card__actions');
                
                if (customerSection) customerSection.remove();
                orderSections.forEach(section => section.remove());
                if (actionsSection) actionsSection.remove();
                
                // بررسی اینکه آیا بخش خالی وجود دارد یا نه
                let emptySection = tableCard.querySelector('.table-card__empty');
                if (!emptySection) {
                    emptySection = document.createElement('div');
                    emptySection.className = 'table-card__empty';
                    emptySection.textContent = 'میز آماده پذیرش';
                    tableCard.appendChild(emptySection);
                }
            }
            
            alert(`میز با موفقیت تسویه شد. شماره فاکتور: ${data.invoice_number}`);
            
            // به‌روزرسانی صفحه برای به‌روزرسانی آمار و اطمینان از همگام‌سازی
            setTimeout(() => {
            location.reload();
            }, 500);
        } else {
            alert(data.message || 'خطا در تسویه میز');
        }
    } catch (error) {
        console.error('خطا در تسویه میز:', error);
        alert('خطا در تسویه میز');
    }
}

// تابع جستجوی مشتری برای میز
// تابع برای بررسی و نمایش/مخفی کردن فیلد تاریخ تولد
function checkAndToggleBirthDateField() {
    const nameInput = document.getElementById('table-customer-name');
    const phoneInput = document.getElementById('table-customer-phone');
    const birthDateGroup = document.getElementById('table-customer-birth-date-group');
    const birthDateInput = document.getElementById('table-customer-birth-date');
    
    if (!nameInput || !phoneInput || !birthDateGroup) return;
    
    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    
    // اگر نام یا شماره تماس خالی است، فیلد تاریخ تولد را مخفی کن
    if (!name && !phone) {
        birthDateGroup.style.display = 'none';
        return;
    }
    
    // بررسی اینکه آیا مشتری موجود است یا نه
    const searchQuery = name || phone;
    if (searchQuery.length < 2) {
        birthDateGroup.style.display = 'none';
        return;
    }
    
    fetch(`/customer/search?q=${encodeURIComponent(searchQuery)}`)
        .then(res => res.json())
        .then(data => {
            // بررسی اینکه آیا مشتری پیدا شده و سفارش قبلی دارد یا نه
            let isExistingCustomer = false;
            if (data.length > 0) {
                // اگر نام و شماره تماس هر دو موجود است، دقیق‌تر بررسی کن
                if (name && phone) {
                    const exactMatch = data.find(c => 
                        c.name === name && c.phone === phone
                    );
                    if (exactMatch) {
                        isExistingCustomer = exactMatch.has_orders;
                        if (exactMatch.birth_date && birthDateInput) {
                            birthDateInput.value = exactMatch.birth_date;
                        }
                    } else {
                        // اگر دقیق پیدا نشد، اولین نتیجه را بررسی کن
                        isExistingCustomer = data[0].has_orders;
                    }
                } else {
                    // اگر فقط نام یا فقط شماره تماس موجود است
                    isExistingCustomer = data[0].has_orders;
                    if (data[0].birth_date && birthDateInput) {
                        birthDateInput.value = data[0].birth_date;
                    }
                }
            }
            
            // اگر مشتری جدید است (سفارش قبلی ندارد)، فیلد تاریخ تولد را نمایش بده
            if (!isExistingCustomer) {
                birthDateGroup.style.display = 'block';
            } else {
                birthDateGroup.style.display = 'none';
            }
        })
        .catch(err => {
            console.error("Error checking customer:", err);
            // در صورت خطا، فیلد را مخفی کن
            birthDateGroup.style.display = 'none';
        });
}

// متغیر global برای نگه‌داری وضعیت مشتری جدید
let isNewCustomer = false;

function initTableCustomerSearch() {
    const nameInput = document.getElementById('table-customer-name');
    const phoneInput = document.getElementById('table-customer-phone');
    const nameResults = document.getElementById('table-customer-results');
    const phoneResults = document.getElementById('table-customer-phone-results');
    const registerBtnGroup = document.getElementById('register-new-customer-group');
    const registerBtn = document.getElementById('register-new-customer-btn');
    
    let nameSearchTimeout = null;
    let phoneSearchTimeout = null;
    
    // تابع برای بررسی و نمایش/مخفی کردن دکمه ثبت مشتری جدید
    function checkAndShowRegisterButton() {
        const name = nameInput ? nameInput.value.trim() : '';
        const phone = phoneInput ? phoneInput.value.trim() : '';
        
        if (!registerBtnGroup) return;
        
        // اگر نام و شماره موبایل پر شده باشد
        if (name && phone) {
            // بررسی اینکه آیا مشتری در نتایج جستجو پیدا شده است یا نه
            const hasValidSearchResults = nameResults && 
                                        nameResults.style.display === 'block' && 
                                        nameResults.innerHTML !== '' && 
                                        !nameResults.innerHTML.includes('مشتری یافت نشد') &&
                                        !nameResults.innerHTML.includes('خطا') &&
                                        nameResults.querySelector('.customer-result'); // بررسی وجود نتیجه معتبر
            
            // اگر مشتری یافت نشده بود (isNewCustomer = true) یا هنوز جستجو نشده (hasValidSearchResults = false)
            // یا اگر پیام "مشتری یافت نشد" نمایش داده شده، دکمه را نمایش بده
            if (isNewCustomer || !hasValidSearchResults || nameResults.innerHTML.includes('مشتری یافت نشد')) {
                registerBtnGroup.style.display = 'block';
            } else {
                // اگر مشتری پیدا شده بود، دکمه را مخفی کن
                registerBtnGroup.style.display = 'none';
            }
        } else {
            // اگر نام یا شماره موبایل خالی است، دکمه را مخفی کن
            registerBtnGroup.style.display = 'none';
        }
    }
    
    // رویداد کلیک روی دکمه ثبت مشتری جدید
    if (registerBtn) {
        registerBtn.addEventListener('click', async function() {
            const name = nameInput ? nameInput.value.trim() : '';
            const phone = phoneInput ? phoneInput.value.trim() : '';
            const birthDateInput = document.getElementById('table-customer-birth-date');
            const birthDate = birthDateInput && birthDateInput.value ? birthDateInput.value : '';
            
            if (!name) {
                alert('لطفاً نام مشتری را وارد کنید');
                return;
            }
            
            try {
                const response = await fetch('/customer/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: name,
                        phone: phone || null,
                        birth_date: birthDate || null
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('مشتری با موفقیت ثبت شد');
                    isNewCustomer = false;
                    if (registerBtnGroup) registerBtnGroup.style.display = 'none';
                    // پاک کردن پیام "مشتری یافت نشد"
                    if (nameResults) {
                        nameResults.innerHTML = '';
                        nameResults.style.display = 'none';
                    }
                    if (phoneResults) {
                        phoneResults.innerHTML = '';
                        phoneResults.style.display = 'none';
                    }
                    // به‌روزرسانی اطلاعات مشتری
                    updateTableCustomer();
                } else {
                    alert(data.message || 'خطا در ثبت مشتری');
                }
            } catch (error) {
                console.error('خطا در ثبت مشتری:', error);
                alert('خطا در ثبت مشتری');
            }
        });
    }
    
    // جستجو بر اساس نام
    if (nameInput && nameResults) {
        nameInput.addEventListener('input', function() {
            clearTimeout(nameSearchTimeout);
            const q = nameInput.value.trim();
            if (q.length < 2) {
                nameResults.innerHTML = '';
                nameResults.style.display = 'none';
                checkAndToggleBirthDateField();
                return;
            }
            nameSearchTimeout = setTimeout(() => {
                fetch(`/customer/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        nameResults.innerHTML = '';
                        if (data.length === 0) {
                            // فقط یک بار پیام "مشتری یافت نشد" را نمایش بده (فقط در فیلد نام)
                            nameResults.innerHTML = '<div class="no-result">مشتری یافت نشد</div>';
                            isNewCustomer = true;
                            // اگر مشتری پیدا نشد، فیلد تاریخ تولد را نمایش بده (مشتری جدید)
                            const birthDateGroup = document.getElementById('table-customer-birth-date-group');
                            if (birthDateGroup) birthDateGroup.style.display = 'block';
                            // بررسی و نمایش دکمه ثبت مشتری جدید (با تاخیر برای اطمینان از به‌روزرسانی DOM)
                            setTimeout(() => {
                                checkAndShowRegisterButton();
                            }, 100);
                        } else {
                            isNewCustomer = false;
                            if (registerBtnGroup) registerBtnGroup.style.display = 'none';
                            data.forEach(c => {
                                const div = document.createElement('div');
                                div.className = 'customer-result';
                                div.textContent = `${c.name}${c.phone ? ' (' + c.phone + ')' : ''}`;
                                div.addEventListener('click', function() {
                                    nameInput.value = c.name;
                                    if (phoneInput) phoneInput.value = c.phone || '';
                                    nameResults.innerHTML = '';
                                    nameResults.style.display = 'none';
                                    isNewCustomer = false;
                                    if (registerBtnGroup) registerBtnGroup.style.display = 'none';
                                    
                                    // بررسی و نمایش/مخفی کردن فیلد تاریخ تولد
                                    const birthDateGroup = document.getElementById('table-customer-birth-date-group');
                                    const birthDateInput = document.getElementById('table-customer-birth-date');
                                    if (c.has_orders) {
                                        // مشتری قدیمی است
                                        if (birthDateGroup) birthDateGroup.style.display = 'none';
                                    } else {
                                        // مشتری جدید است
                                        if (birthDateGroup) birthDateGroup.style.display = 'block';
                                    }
                                    if (c.birth_date && birthDateInput) {
                                        birthDateInput.value = c.birth_date;
                                    }
                                    
                                    updateTableCustomer();
                                });
                                nameResults.appendChild(div);
                            });
                            checkAndToggleBirthDateField();
                        }
                        nameResults.style.display = 'block';
                    })
                    .catch(err => {
                        console.error("Customer search error:", err);
                        nameResults.innerHTML = '<div class="no-result">خطا در جستجو</div>';
                        nameResults.style.display = 'block';
                    });
            }, 300);
        });
        
        // بررسی هنگام blur (وقتی کاربر از فیلد خارج می‌شود)
        nameInput.addEventListener('blur', function() {
            setTimeout(checkAndToggleBirthDateField, 200);
            checkAndShowRegisterButton();
        });
        
        // بررسی هنگام تغییر مقدار برای نمایش دکمه ثبت
        nameInput.addEventListener('input', function() {
            checkAndShowRegisterButton();
        });
    }
    
    // جستجو بر اساس شماره تماس
    if (phoneInput && phoneResults) {
        phoneInput.addEventListener('input', function() {
            clearTimeout(phoneSearchTimeout);
            const q = phoneInput.value.trim();
            if (q.length < 2) {
                phoneResults.innerHTML = '';
                phoneResults.style.display = 'none';
                checkAndToggleBirthDateField();
                return;
            }
            phoneSearchTimeout = setTimeout(() => {
                fetch(`/customer/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        phoneResults.innerHTML = '';
                        if (data.length === 0) {
                            // در فیلد شماره تماس پیام "مشتری یافت نشد" را نمایش نده
                            // اگر قبلاً در فیلد نام یافت نشده بود یا الان یافت نشد، دکمه ثبت را نمایش بده
                            isNewCustomer = true;
                            // اگر مشتری پیدا نشد، فیلد تاریخ تولد را نمایش بده (مشتری جدید)
                            const birthDateGroup = document.getElementById('table-customer-birth-date-group');
                            if (birthDateGroup) birthDateGroup.style.display = 'block';
                            // بررسی و نمایش دکمه ثبت مشتری جدید
                            setTimeout(() => {
                                checkAndShowRegisterButton();
                            }, 100);
                        } else {
                            isNewCustomer = false;
                            if (registerBtnGroup) registerBtnGroup.style.display = 'none';
                            data.forEach(c => {
                                const div = document.createElement('div');
                                div.className = 'customer-result';
                                div.textContent = `${c.name}${c.phone ? ' (' + c.phone + ')' : ''}`;
                                div.addEventListener('click', function() {
                                    phoneInput.value = c.phone || '';
                                    if (nameInput) nameInput.value = c.name;
                                    phoneResults.innerHTML = '';
                                    phoneResults.style.display = 'none';
                                    isNewCustomer = false;
                                    if (registerBtnGroup) registerBtnGroup.style.display = 'none';
                                    
                                    // بررسی و نمایش/مخفی کردن فیلد تاریخ تولد
                                    const birthDateGroup = document.getElementById('table-customer-birth-date-group');
                                    const birthDateInput = document.getElementById('table-customer-birth-date');
                                    if (c.has_orders) {
                                        // مشتری قدیمی است
                                        if (birthDateGroup) birthDateGroup.style.display = 'none';
                                    } else {
                                        // مشتری جدید است
                                        if (birthDateGroup) birthDateGroup.style.display = 'block';
                                    }
                                    if (c.birth_date && birthDateInput) {
                                        birthDateInput.value = c.birth_date;
                                    }
                                    
                                    updateTableCustomer();
                                });
                                phoneResults.appendChild(div);
                            });
                            checkAndToggleBirthDateField();
                        }
                        phoneResults.style.display = 'block';
                    })
                    .catch(err => {
                        console.error("Customer search error:", err);
                        phoneResults.innerHTML = '<div class="no-result">خطا در جستجو</div>';
                        phoneResults.style.display = 'block';
                    });
            }, 300);
        });
        
        // بررسی هنگام blur (وقتی کاربر از فیلد خارج می‌شود)
        phoneInput.addEventListener('blur', function() {
            setTimeout(checkAndToggleBirthDateField, 200);
            checkAndShowRegisterButton();
        });
        
        // بررسی هنگام تغییر مقدار برای نمایش دکمه ثبت
        phoneInput.addEventListener('input', function() {
            checkAndShowRegisterButton();
        });
    }
    
    // بررسی تغییر تاریخ تولد برای نمایش دکمه ثبت
    const birthDateInput = document.getElementById('table-customer-birth-date');
    if (birthDateInput) {
        birthDateInput.addEventListener('change', function() {
            checkAndShowRegisterButton();
        });
    }
    
    // بستن نتایج با کلیک خارج
    document.addEventListener('click', function(e) {
        if (nameInput && nameResults && !nameResults.contains(e.target) && e.target !== nameInput) {
            nameResults.style.display = 'none';
        }
        if (phoneInput && phoneResults && !phoneResults.contains(e.target) && e.target !== phoneInput) {
            phoneResults.style.display = 'none';
        }
    });
}

// رویدادهای کلیک
document.addEventListener('DOMContentLoaded', function() {
    // کلیک روی کارت میز
    document.querySelectorAll('.table-card').forEach(card => {
        card.addEventListener('click', function(e) {
            // اگر روی دکمه‌ها یا لینک‌ها کلیک شده، modal باز نشود
            if (e.target.tagName === 'BUTTON' || 
                e.target.tagName === 'A' ||
                e.target.closest('button') ||
                e.target.closest('a') ||
                e.target.closest('.table-card__actions') ||
                e.target.closest('.table-card__checkout') ||
                e.target.closest('.table-card__checkout-options')) {
                return;
            }
            
            const tableId = parseInt(this.getAttribute('data-table-id'));
            const tableNumber = parseInt(this.getAttribute('data-table-number'));
            
            if (tableId && tableNumber) {
                console.log('Opening table modal for table:', tableId, tableNumber);
                openTableModal(tableId, tableNumber);
            } else {
                console.error('Table ID or Number not found:', tableId, tableNumber);
            }
        });
    });
    
    // کلیک روی آیتم منو (استفاده از event delegation به عنوان fallback)
    // event listener مستقیم در openTableModal تنظیم می‌شود
    document.addEventListener('click', function(e) {
        const menuItem = e.target.closest('#table-modal .menu-item-selectable');
        if (menuItem) {
            // بررسی اینکه modal باز است
            const modal = document.getElementById('table-modal');
            if (modal && modal.style.display === 'flex' && currentTableId) {
                e.stopPropagation(); // جلوگیری از انتشار event به modal
                e.preventDefault(); // جلوگیری از رفتار پیش‌فرض
                const itemId = parseInt(menuItem.getAttribute('data-item-id'));
                if (itemId && !isNaN(itemId)) {
                    console.log('Adding item to table (fallback):', itemId);
                    addItemToTable(itemId);
                    return false;
                }
            }
        }
    }, true); // استفاده از capture phase
    
    // به‌روزرسانی خودکار اطلاعات مشتری
    const nameInput = document.getElementById('table-customer-name');
    const phoneInput = document.getElementById('table-customer-phone');
    const discountAmountInput = document.getElementById('table-discount-amount');
    const discountPercentInput = document.getElementById('table-discount-percent');
    
    if (nameInput) {
        nameInput.addEventListener('blur', updateTableCustomer);
    }
    if (phoneInput) {
        phoneInput.addEventListener('blur', updateTableCustomer);
    }
    if (discountAmountInput) {
        discountAmountInput.addEventListener('input', function() {
            // به‌روزرسانی محاسبات به صورت real-time
            updateTableTotals();
        });
        
        discountAmountInput.addEventListener('blur', function() {
            // ذخیره در دیتابیس
            updateTableCustomer();
        });
    }
    if (discountPercentInput) {
        discountPercentInput.addEventListener('input', function() {
            // به‌روزرسانی محاسبات به صورت real-time
            updateTableTotals();
        });
        
        discountPercentInput.addEventListener('blur', function() {
            // ذخیره در دیتابیس
            updateTableCustomer();
        });
    }
        
        // دکمه اعمال تخفیف - استفاده از event delegation برای اطمینان از کارکرد
        // Event listener در بخش event delegation اضافه می‌شود
    
    // دکمه‌های ثبت و تسویه
    // استفاده از event delegation برای دکمه‌های modal (fallback)
    document.addEventListener('click', function(e) {
        const tableModal = document.getElementById('table-modal');
        if (!tableModal || tableModal.style.display !== 'flex') {
            return;
        }
        
        // بررسی کلیک روی دکمه اعمال تخفیف عددی
        const applyDiscountAmountBtn = e.target.closest('#apply-table-discount-amount') || (e.target.id === 'apply-table-discount-amount' ? e.target : null);
        if (applyDiscountAmountBtn) {
            // بررسی اینکه آیا دکمه قبلاً غیرفعال شده است
            if (applyDiscountAmountBtn.disabled) {
                return false;
            }
            
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('دکمه اعمال تخفیف عددی کلیک شد');
            
            // غیرفعال کردن دکمه برای جلوگیری از کلیک مجدد
            applyDiscountAmountBtn.disabled = true;
            applyDiscountAmountBtn.style.opacity = '0.5';
            applyDiscountAmountBtn.style.cursor = 'not-allowed';
            applyDiscountAmountBtn.title = 'تخفیف اعمال شده است';
            
            // به‌روزرسانی محاسبات به صورت لحظه‌ای قبل از ارسال
            updateTableTotals();
            
            // ارسال به سرور
            updateTableCustomer().then(() => {
                console.log('تخفیف عددی با موفقیت اعمال شد');
                // نمایش بازخورد بصری
                applyDiscountAmountBtn.textContent = '✓';
                applyDiscountAmountBtn.style.background = 'var(--color-success)';
                // به‌روزرسانی محاسبات بعد از اعمال تخفیف
                updateTableTotals();
            }).catch(err => {
                console.error('خطا در اعمال تخفیف عددی:', err);
                // در صورت خطا، دکمه را دوباره فعال کن
                applyDiscountAmountBtn.disabled = false;
                applyDiscountAmountBtn.style.opacity = '1';
                applyDiscountAmountBtn.style.cursor = 'pointer';
                applyDiscountAmountBtn.title = 'اعمال تخفیف عددی';
            });
            
            return false;
        }
        
        // بررسی کلیک روی دکمه اعمال تخفیف درصدی
        const applyDiscountPercentBtn = e.target.closest('#apply-table-discount-percent') || (e.target.id === 'apply-table-discount-percent' ? e.target : null);
        if (applyDiscountPercentBtn) {
            // بررسی اینکه آیا دکمه قبلاً غیرفعال شده است
            if (applyDiscountPercentBtn.disabled) {
                return false;
            }
            
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('دکمه اعمال تخفیف درصدی کلیک شد');
            
            // غیرفعال کردن دکمه برای جلوگیری از کلیک مجدد
            applyDiscountPercentBtn.disabled = true;
            applyDiscountPercentBtn.style.opacity = '0.5';
            applyDiscountPercentBtn.style.cursor = 'not-allowed';
            applyDiscountPercentBtn.title = 'تخفیف اعمال شده است';
            
            // به‌روزرسانی محاسبات به صورت لحظه‌ای قبل از ارسال
            updateTableTotals();
            
            // ارسال به سرور
            updateTableCustomer().then(() => {
                console.log('تخفیف درصدی با موفقیت اعمال شد');
                // نمایش بازخورد بصری
                applyDiscountPercentBtn.textContent = '✓';
                applyDiscountPercentBtn.style.background = 'var(--color-success)';
                // به‌روزرسانی محاسبات بعد از اعمال تخفیف
                updateTableTotals();
            }).catch(err => {
                console.error('خطا در اعمال تخفیف درصدی:', err);
                // در صورت خطا، دکمه را دوباره فعال کن
                applyDiscountPercentBtn.disabled = false;
                applyDiscountPercentBtn.style.opacity = '1';
                applyDiscountPercentBtn.style.cursor = 'pointer';
                applyDiscountPercentBtn.title = 'اعمال تخفیف درصدی';
            });
            
            return false;
        }
        
        // بررسی کلیک روی دکمه ثبت میز
        if (e.target && (e.target.id === 'submit-table-order' || e.target.closest('#submit-table-order'))) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Submit button clicked via delegation!');
            submitTableOrder();
            return false;
        }
        
        // بررسی کلیک روی دکمه تسویه میز
        if (e.target && (e.target.id === 'checkout-table' || e.target.closest('#checkout-table'))) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Checkout button clicked via delegation!');
            checkoutTable();
            return false;
        }
    }, true); // استفاده از capture phase
    
    // بستن مودال با کلیک روی پس‌زمینه
    const tableModal = document.getElementById('table-modal');
    if (tableModal) {
        tableModal.addEventListener('click', function(e) {
            // فقط اگر روی خود modal کلیک شده (نه روی محتوای داخل آن)
            if (e.target === this) {
                closeTableModal();
            }
        });
        
        // جلوگیری از بسته شدن modal وقتی روی محتوای آن کلیک می‌شود
        const modalContent = tableModal.querySelector('.table-modal-content');
        if (modalContent) {
            modalContent.addEventListener('click', function(e) {
                e.stopPropagation(); // جلوگیری از انتشار event به modal
            });
        }
    }
    
    // راه‌اندازی جستجوی مشتری
    initTableCustomerSearch();
});

// توابع انتقال میز
async function openTransferTableModal() {
    if (!currentTableId || !currentTableNumber) {
        alert('لطفاً ابتدا یک میز را انتخاب کنید');
        return;
    }
    
    const modal = document.getElementById('transfer-table-modal');
    const fromTableNumberEl = document.getElementById('transfer-from-table-number');
    const selectEl = document.getElementById('transfer-to-table-select');
    
    if (!modal || !fromTableNumberEl || !selectEl) {
        console.error('Transfer table modal elements not found');
        return;
    }
    
    // نمایش شماره میز مبدا
    fromTableNumberEl.textContent = currentTableNumber;
    
    // بارگذاری لیست میزها
    try {
        const response = await fetch('/table/list');
        const data = await response.json();
        
        if (data.success && data.tables) {
            // پاک کردن options قبلی (به جز option اول)
            selectEl.innerHTML = '<option value="">-- انتخاب میز --</option>';
            
            // اضافه کردن میزها (به جز میز فعلی)
            data.tables.forEach(table => {
                if (table.id !== currentTableId) {
                    const option = document.createElement('option');
                    option.value = table.id;
                    const statusLabel = table.status === 'خالی' ? ' (خالی)' : ' (اشغال شده)';
                    option.textContent = `میز ${table.number}${statusLabel}`;
                    selectEl.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error('خطا در دریافت لیست میزها:', error);
        alert('خطا در دریافت لیست میزها');
        return;
    }
    
    modal.style.display = 'flex';
}

function closeTransferTableModal() {
    const modal = document.getElementById('transfer-table-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function confirmTransferTable() {
    if (!currentTableId) {
        alert('خطا: میز انتخاب نشده است');
        return;
    }
    
    const selectEl = document.getElementById('transfer-to-table-select');
    if (!selectEl) {
        alert('خطا: عنصر انتخاب میز یافت نشد');
        return;
    }
    
    const targetTableId = selectEl.value;
    if (!targetTableId) {
        alert('لطفاً میز مقصد را انتخاب کنید');
        return;
    }
    
    if (!confirm('آیا مطمئن هستید که می‌خواهید تمام سفارش‌های این میز را منتقل کنید؟')) {
        return;
    }
    
    try {
        const response = await fetch(`/table/${currentTableId}/transfer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_table_id: parseInt(targetTableId)
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            closeTransferTableModal();
            closeTableModal();
            // به‌روزرسانی صفحه برای نمایش تغییرات
            location.reload();
        } else {
            alert(data.message || 'خطا در انتقال میز');
        }
    } catch (error) {
        console.error('خطا در انتقال میز:', error);
        alert('خطا در انتقال میز: ' + error.message);
    }
}

// اطمینان از دسترسی global به توابع برای onclick handlers
window.printTableInvoice = printTableInvoice;
window.settleTableFromDashboard = settleTableFromDashboard;
window.toggleCheckoutOptions = toggleCheckoutOptions;
window.openTransferTableModal = openTransferTableModal;
window.closeTransferTableModal = closeTransferTableModal;
window.confirmTransferTable = confirmTransferTable;
