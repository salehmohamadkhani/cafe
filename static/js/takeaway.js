let currentTakeawayId = null;
let currentTakeawayStatus = null;
let takeawayItems = [];

// باز کردن پاپ‌آپ سفارش بیرون‌بر جدید
async function openNewTakeawayModal() {
    try {
        const response = await fetch('/takeaway/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: 'مشتری ناشناس',
                customer_phone: '',
                discount: 0
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            currentTakeawayId = data.order_id;
            const modal = document.getElementById('takeaway-modal');
            document.getElementById('takeaway-modal-invoice').textContent = `#${data.invoice_number}`;
            modal.style.display = 'flex';
            
            // بارگذاری اطلاعات سفارش برای تنظیم currentTakeawayStatus
            await loadTakeawayData(data.order_id);
            
            // تنظیم event listener برای دکمه‌های ثبت و تسویه (باید هر بار که modal باز می‌شود تنظیم شود)
            setTimeout(() => {
                const submitBtn = document.getElementById('submit-takeaway-order');
                const checkoutBtn = document.getElementById('checkout-takeaway-order');
                
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
                        console.log('Submit takeaway button clicked!');
                        submitTakeawayOrder(currentTakeawayId);
                        return false;
                    }, true); // استفاده از capture phase
                }
                
                if (checkoutBtn) {
                    // حذف تمام event listener های قبلی
                    const newCheckoutBtn = checkoutBtn.cloneNode(true);
                    checkoutBtn.parentNode.replaceChild(newCheckoutBtn, checkoutBtn);
                    
                    // اضافه کردن event listener جدید برای نمایش dropdown
                    newCheckoutBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        console.log('Checkout takeaway button clicked!');
                        toggleTakeawayModalCheckoutOptions();
                        return false;
                    }, true); // استفاده از capture phase
                }
            }, 200);
            
            // تنظیم event listener مستقیم روی آیتم‌های منو
            setTimeout(() => {
                const menuItems = modal.querySelectorAll('.menu-item-selectable');
                menuItems.forEach(item => {
                    // حذف event listener های قبلی و اضافه کردن جدید
                    const newItem = item.cloneNode(true);
                    item.parentNode.replaceChild(newItem, item);
                    
                    // اضافه کردن event listener جدید
                    newItem.addEventListener('click', function(e) {
                        e.stopPropagation(); // جلوگیری از انتشار event به modal
                        e.preventDefault(); // جلوگیری از رفتار پیش‌فرض
                        e.stopImmediatePropagation(); // جلوگیری از اجرای سایر listener ها
                        const itemId = parseInt(newItem.getAttribute('data-item-id'));
                        if (itemId && !isNaN(itemId) && currentTakeawayId) {
                            console.log('Adding item to takeaway (direct):', itemId);
                            addItemToTakeaway(itemId);
                        }
                        return false;
                    }, true); // استفاده از capture phase
                });
            }, 100);
            
            // راه‌اندازی مجدد جستجوی مشتری بعد از باز شدن modal
            setTimeout(() => {
                initTakeawayCustomerSearch();
            }, 100);
        } else {
            alert(data.message || 'خطا در ایجاد سفارش');
        }
    } catch (error) {
        console.error('خطا در ایجاد سفارش بیرون‌بر:', error);
        if (error.message) {
            alert('خطا در ایجاد سفارش بیرون‌بر: ' + error.message);
        } else {
            alert('خطا در ایجاد سفارش بیرون‌بر. لطفاً صفحه را refresh کنید و دوباره تلاش کنید.');
        }
    }
}

// تابع جستجوی مشتری برای سفارشات بیرون‌بر
let takeawayNameSearchTimeout = null;
let takeawayPhoneSearchTimeout = null;

function initTakeawayCustomerSearch() {
    const nameInput = document.getElementById('takeaway-customer-name');
    const phoneInput = document.getElementById('takeaway-customer-phone');
    const nameResults = document.getElementById('takeaway-customer-results');
    const phoneResults = document.getElementById('takeaway-customer-phone-results');
    
    // جستجو بر اساس نام
    if (nameInput && nameResults) {
        // حذف event listener قبلی
        const newNameInput = nameInput.cloneNode(true);
        nameInput.parentNode.replaceChild(newNameInput, nameInput);
        
        newNameInput.addEventListener('input', function() {
            clearTimeout(takeawayNameSearchTimeout);
            const q = newNameInput.value.trim();
            if (q.length < 2) {
                nameResults.innerHTML = '';
                nameResults.style.display = 'none';
                return;
            }
            takeawayNameSearchTimeout = setTimeout(() => {
                fetch(`/customer/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        nameResults.innerHTML = '';
                        if (data.length === 0) {
                            nameResults.innerHTML = '<div class="no-result">مشتری یافت نشد</div>';
                        } else {
                            data.forEach(c => {
                                const div = document.createElement('div');
                                div.className = 'customer-result';
                                div.innerHTML = `
                                    <span class="customer-result__name">${c.name || ''}</span>
                                    <span class="customer-result__phone">${c.phone || ''}</span>
                                `;
                                div.addEventListener('click', function() {
                                    // پیدا کردن input های فعلی (ممکن است بعد از clone تغییر کرده باشند)
                                    const nameField = document.getElementById('takeaway-customer-name');
                                    const phoneField = document.getElementById('takeaway-customer-phone');
                                    
                                    if (nameField) nameField.value = c.name || '';
                                    if (phoneField) phoneField.value = c.phone || '';
                                    
                                    nameResults.innerHTML = '';
                                    nameResults.style.display = 'none';
                                    
                                    // به‌روزرسانی اطلاعات مشتری
                                    if (currentTakeawayId) {
                                        updateTakeawayCustomer();
                                    }
                                });
                                nameResults.appendChild(div);
                            });
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
    }
    
    // جستجو بر اساس شماره تماس
    if (phoneInput && phoneResults) {
        // حذف event listener قبلی
        const newPhoneInput = phoneInput.cloneNode(true);
        phoneInput.parentNode.replaceChild(newPhoneInput, phoneInput);
        
        newPhoneInput.addEventListener('input', function() {
            clearTimeout(takeawayPhoneSearchTimeout);
            const q = newPhoneInput.value.trim();
            if (q.length < 2) {
                phoneResults.innerHTML = '';
                phoneResults.style.display = 'none';
                return;
            }
            takeawayPhoneSearchTimeout = setTimeout(() => {
                fetch(`/customer/search?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(data => {
                        phoneResults.innerHTML = '';
                        if (data.length === 0) {
                            phoneResults.innerHTML = '<div class="no-result">مشتری یافت نشد</div>';
                        } else {
                            data.forEach(c => {
                                const div = document.createElement('div');
                                div.className = 'customer-result';
                                div.innerHTML = `
                                    <span class="customer-result__name">${c.name || ''}</span>
                                    <span class="customer-result__phone">${c.phone || ''}</span>
                                `;
                                div.addEventListener('click', function() {
                                    // پیدا کردن input های فعلی (ممکن است بعد از clone تغییر کرده باشند)
                                    const nameField = document.getElementById('takeaway-customer-name');
                                    const phoneField = document.getElementById('takeaway-customer-phone');
                                    
                                    if (nameField) nameField.value = c.name || '';
                                    if (phoneField) phoneField.value = c.phone || '';
                                    
                                    phoneResults.innerHTML = '';
                                    phoneResults.style.display = 'none';
                                    
                                    // به‌روزرسانی اطلاعات مشتری
                                    if (currentTakeawayId) {
                                        updateTakeawayCustomer();
                                    }
                                });
                                phoneResults.appendChild(div);
                            });
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
    }
}

// باز کردن پاپ‌آپ سفارش بیرون‌بر موجود
async function openTakeawayModal(orderId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    currentTakeawayId = orderId;
    const modal = document.getElementById('takeaway-modal');
    modal.style.display = 'flex';
    await loadTakeawayData(orderId);
    
    // راه‌اندازی مجدد جستجوی مشتری بعد از باز شدن modal
    setTimeout(() => {
        initTakeawayCustomerSearch();
    }, 100);
    
    // تنظیم event listener برای دکمه‌های ثبت و تسویه (باید هر بار که modal باز می‌شود تنظیم شود)
    setTimeout(() => {
        const submitBtn = document.getElementById('submit-takeaway-order');
        const checkoutBtn = document.getElementById('checkout-takeaway-order');
        
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
                console.log('Submit takeaway button clicked!');
                submitTakeawayOrder(currentTakeawayId);
                return false;
            }, true); // استفاده از capture phase
        }
        
        if (checkoutBtn) {
            // حذف تمام event listener های قبلی
            const newCheckoutBtn = checkoutBtn.cloneNode(true);
            checkoutBtn.parentNode.replaceChild(newCheckoutBtn, checkoutBtn);
            
            // اضافه کردن event listener جدید برای نمایش dropdown
            newCheckoutBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('Checkout takeaway button clicked!');
                toggleTakeawayModalCheckoutOptions();
                return false;
            }, true); // استفاده از capture phase
        }
    }, 200);
    
    // تنظیم event listener مستقیم روی آیتم‌های منو
    setTimeout(() => {
        const menuItems = modal.querySelectorAll('.menu-item-selectable');
        menuItems.forEach(item => {
            // حذف event listener های قبلی و اضافه کردن جدید
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);
            
            // اضافه کردن event listener جدید
            newItem.addEventListener('click', function(e) {
                e.stopPropagation(); // جلوگیری از انتشار event به modal
                e.preventDefault(); // جلوگیری از رفتار پیش‌فرض
                e.stopImmediatePropagation(); // جلوگیری از اجرای سایر listener ها
                const itemId = parseInt(newItem.getAttribute('data-item-id'));
                if (itemId && !isNaN(itemId) && currentTakeawayId) {
                    console.log('Adding item to takeaway (direct):', itemId);
                    addItemToTakeaway(itemId);
                }
                return false;
            }, true); // استفاده از capture phase
        });
    }, 100);
    
    // راه‌اندازی مجدد جستجوی مشتری بعد از باز شدن modal
    setTimeout(() => {
        initTakeawayCustomerSearch();
    }, 100);
}

// بستن پاپ‌آپ
function closeTakeawayModal() {
    document.getElementById('takeaway-modal').style.display = 'none';
    currentTakeawayId = null;
    takeawayItems = [];
    clearTakeawayForm();
}

async function cancelCurrentTakeawayOrder() {
    // اگر هنوز سفارشی ساخته نشده، فقط مودال را ببند
    if (!currentTakeawayId) {
        closeTakeawayModal();
        return;
    }

    const confirmed = confirm('آیا از حذف این سفارش بیرون‌بر مطمئن هستید؟');
    if (!confirmed) return;

    // از همان API موجود برای حذف سفارش استفاده می‌کنیم
    // deleteTakeawayOrder خودش صفحه را reload می‌کند، پس نیازی به بستن مودال نیست
    await deleteTakeawayOrder(currentTakeawayId);
}

// بارگذاری اطلاعات سفارش بیرون‌بر
async function loadTakeawayData(orderId) {
    try {
        const response = await fetch(`/takeaway/${orderId}`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.id) {
            throw new Error('سفارش یافت نشد');
        }
        
        document.getElementById('takeaway-modal-invoice').textContent = `#${data.invoice_number}`;
        document.getElementById('takeaway-customer-name').value = data.customer_name || '';
        document.getElementById('takeaway-customer-phone').value = data.customer_phone || '';
        
        // پر کردن فیلدهای تخفیف
        const discountAmount = data.discount_amount || 0;
        const discountPercent = data.discount_percent || 0;
        document.getElementById('takeaway-discount-amount').value = discountAmount;
        document.getElementById('takeaway-discount-percent').value = discountPercent;
        
        // اگر تخفیف قبلاً اعمال شده، دکمه‌ها را غیرفعال کن
        const applyDiscountAmountBtn = document.getElementById('apply-takeaway-discount-amount');
        const applyDiscountPercentBtn = document.getElementById('apply-takeaway-discount-percent');
        
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
        
        takeawayItems = data.items || [];
        currentTakeawayStatus = data.status || null; // ذخیره وضعیت سفارش
        renderTakeawayItems();
        
        // تغییر متن دکمه "ثبت سفارش" به "اصلاح سفارش" اگر سفارش قبلاً ثبت شده باشد
        const submitBtn = document.getElementById('submit-takeaway-order');
        if (submitBtn) {
            if (currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده' && takeawayItems.length > 0) {
                submitBtn.textContent = 'اصلاح سفارش';
            } else {
                submitBtn.textContent = 'ثبت سفارش';
            }
        }
        
        // به‌روزرسانی محاسبات با استفاده از داده‌های بارگذاری شده از سرور
        // استفاده از مقادیر از سرور به جای محاسبه محلی
        const totalAmount = data.total_amount || 0;
        const discount = data.discount || 0;
        const taxAmount = data.tax_amount || 0;
        const finalAmount = data.final_amount || 0;
        
        document.getElementById('takeaway-total-amount').textContent = totalAmount.toLocaleString();
        document.getElementById('takeaway-tax-amount').textContent = taxAmount.toLocaleString();
        document.getElementById('takeaway-final-amount').textContent = finalAmount.toLocaleString();
        
        // نمایش تخفیف در summary - استفاده از updateTakeawayTotals برای محاسبه دقیق
        updateTakeawayTotals();
    } catch (error) {
        console.error('خطا در بارگذاری اطلاعات سفارش:', error);
        alert('خطا در بارگذاری اطلاعات سفارش: ' + error.message);
    }
}

// نمایش آیتم‌های سفارش
function renderTakeawayItems() {
    const container = document.getElementById('takeaway-items-list');
    container.innerHTML = '';
    
    if (takeawayItems.length === 0) {
        container.innerHTML = '<p class="empty-message">هیچ آیتمی انتخاب نشده است</p>';
        return;
    }
    
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
    takeawayItems.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-item-id', item.id);
        tr.innerHTML = `
            <td>${item.menu_item_name}</td>
            <td>${item.unit_price.toLocaleString()}</td>
            <td class="qty-controls-cell">
                <div class="qty-controls">
                    <button type="button" data-item-id="${item.id}" data-action="decrease" class="btn-quantity decrease-qty">-</button>
                    <span class="order-qty">${item.quantity}</span>
                    <button type="button" data-item-id="${item.id}" data-action="increase" class="btn-quantity increase-qty">+</button>
                    <button type="button" data-item-id="${item.id}" data-action="remove" class="btn-remove remove-item" onclick="showTakeawayRemoveReasonField(${item.id})">×</button>
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
                    <input type="text" id="takeaway-removal-reason-${item.id}" class="removal-reason-input" 
                           placeholder="لطفاً دلیل حذف این آیتم را وارد کنید..." 
                           style="flex: 1; padding: 0.5rem; border: 1px solid #ffc107; border-radius: 4px;">
                    <button type="button" data-action="confirm-delete" data-item-id="${item.id}" 
                            class="btn btn-primary" style="padding: 0.5rem 1rem;">تأیید حذف</button>
                    <button type="button" data-action="cancel-delete" data-item-id="${item.id}" 
                            class="btn btn-secondary" style="padding: 0.5rem 1rem;">لغو</button>
                </div>
            </td>
        `;
        tbody.appendChild(reasonRow);
    });
    table.appendChild(tbody);
    
    container.appendChild(table);
}

// افزودن آیتم به سفارش
async function addItemToTakeaway(menuItemId) {
    if (!currentTakeawayId) {
        console.error('currentTakeawayId is null');
        alert('لطفاً ابتدا یک سفارش ایجاد کنید');
        return;
    }
    
    if (!menuItemId || isNaN(menuItemId)) {
        console.error('Invalid menuItemId:', menuItemId);
        return;
    }
    
    console.log('Adding item to takeaway order:', currentTakeawayId, 'item:', menuItemId);
    
    try {
        const response = await fetch(`/takeaway/${currentTakeawayId}/add_item`, {
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
            await loadTakeawayData(currentTakeawayId);
            updateTakeawayCard(currentTakeawayId);
            
            // تغییر دکمه به "اصلاح سفارش" بعد از افزودن آیتم
            const submitBtn = document.getElementById('submit-takeaway-order');
            if (submitBtn && currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده') {
                submitBtn.textContent = 'اصلاح سفارش';
            }
        } else {
            console.error('Server error:', data.message);
            alert(data.message || 'خطا در افزودن آیتم');
        }
    } catch (error) {
        console.error('خطا در افزودن آیتم:', error);
        alert('خطا در افزودن آیتم به سفارش: ' + error.message);
    }
}

// نمایش فیلد دلیل حذف برای سفارش بیرون‌بر
async function showTakeawayRemoveReasonField(itemId) {
    // اگر وضعیت تنظیم نشده، ابتدا بارگذاری کن
    if (currentTakeawayId && !currentTakeawayStatus) {
        await loadTakeawayData(currentTakeawayId);
    }
    
    // اگر سفارش ثبت شده و هنوز تسویه نشده باشد، فیلد دلیل را نمایش بده
    if (currentTakeawayId && currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده') {
        const reasonRow = document.querySelector(`tr.removal-reason-row[data-item-id="${itemId}"]`);
        if (reasonRow) {
            reasonRow.style.display = 'table-row';
            const input = reasonRow.querySelector('.removal-reason-input');
            if (input) {
                input.focus();
            }
        }
    } else {
        // اگر نیاز به دلیل نیست، مستقیماً حذف کن
        removeTakeawayItem(itemId);
    }
}

// مخفی کردن فیلد دلیل حذف برای سفارش بیرون‌بر
function hideTakeawayRemoveReasonField(itemId) {
    const reasonRow = document.querySelector(`tr.removal-reason-row[data-item-id="${itemId}"]`);
    if (reasonRow) {
        reasonRow.style.display = 'none';
        const input = reasonRow.querySelector('.removal-reason-input');
        if (input) {
            input.value = '';
        }
    }
}

// تأیید حذف با دلیل برای سفارش بیرون‌بر
async function confirmRemoveTakeawayItem(itemId) {
    console.log('confirmRemoveTakeawayItem called with itemId:', itemId, 'currentTakeawayId:', currentTakeawayId);
    
    if (!currentTakeawayId) {
        console.error('currentTakeawayId is null');
        alert('خطا: شناسه سفارش یافت نشد');
        return;
    }
    
    const inputId = `takeaway-removal-reason-${itemId}`;
    const input = document.getElementById(inputId);
    console.log('Looking for input with id:', inputId, 'Found:', input);
    
    if (!input) {
        console.error('Input field not found:', inputId);
        alert('خطا: فیلد دلیل حذف یافت نشد');
        return;
    }
    
    const removalReason = input.value.trim();
    console.log('Removal reason:', removalReason);
    
    if (!removalReason) {
        alert('لطفاً دلیل حذف را وارد کنید');
        input.focus();
        return;
    }
    
    try {
        const url = `/takeaway/${currentTakeawayId}/remove_item/${itemId}`;
        console.log('Sending DELETE request to:', url, 'with reason:', removalReason);
        
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ removal_reason: removalReason })
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('HTTP error:', response.status, errorText);
            throw new Error(`خطای سرور: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            await loadTakeawayData(currentTakeawayId);
            updateTakeawayCard(currentTakeawayId);
            
            // تغییر دکمه به "اصلاح سفارش" بعد از حذف آیتم
            const submitBtn = document.getElementById('submit-takeaway-order');
            if (submitBtn && currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده') {
                submitBtn.textContent = 'اصلاح سفارش';
            }
        } else {
            alert(data.message || 'خطا در حذف آیتم');
        }
    } catch (error) {
        console.error('خطا در حذف آیتم:', error);
        alert('خطا در حذف آیتم از سفارش: ' + error.message);
    }
}

// حذف آیتم از سفارش بیرون‌بر (بدون نیاز به دلیل)
async function removeTakeawayItem(itemId) {
    if (!currentTakeawayId) return;
    
    try {
        const response = await fetch(`/takeaway/${currentTakeawayId}/remove_item/${itemId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTakeawayData(currentTakeawayId);
            updateTakeawayCard(currentTakeawayId);
            
            // تغییر دکمه به "اصلاح سفارش" بعد از حذف آیتم
            const submitBtn = document.getElementById('submit-takeaway-order');
            if (submitBtn && currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده') {
                submitBtn.textContent = 'اصلاح سفارش';
            }
        } else {
            // اگر نیاز به دلیل بود، فیلد را نمایش بده
            if (data.requires_reason) {
                await showTakeawayRemoveReasonField(itemId);
            } else {
                alert(data.message || 'خطا در حذف آیتم');
            }
        }
    } catch (error) {
        console.error('خطا در حذف آیتم:', error);
        alert('خطا در حذف آیتم از سفارش');
    }
}

// افزایش تعداد
async function increaseTakeawayItemQuantity(itemId) {
    const item = takeawayItems.find(i => i.id === itemId);
    if (!item) return;
    
    await updateTakeawayItemQuantity(itemId, item.quantity + 1);
}

// کاهش تعداد
async function decreaseTakeawayItemQuantity(itemId) {
    const item = takeawayItems.find(i => i.id === itemId);
    if (!item) return;
    
    if (item.quantity > 1) {
        await updateTakeawayItemQuantity(itemId, item.quantity - 1);
    } else {
        await removeTakeawayItem(itemId);
    }
}

// به‌روزرسانی تعداد
async function updateTakeawayItemQuantity(itemId, quantity) {
    if (!currentTakeawayId) return;
    
    try {
        const response = await fetch(`/takeaway/${currentTakeawayId}/update_item/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity })
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTakeawayData(currentTakeawayId);
            updateTakeawayCard(currentTakeawayId);
            
            // تغییر دکمه به "اصلاح سفارش" بعد از تغییر تعداد
            const submitBtn = document.getElementById('submit-takeaway-order');
            if (submitBtn && currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده') {
                submitBtn.textContent = 'اصلاح سفارش';
            }
        } else {
            alert(data.message || 'خطا در به‌روزرسانی تعداد');
        }
    } catch (error) {
        console.error('خطا در به‌روزرسانی تعداد:', error);
        alert('خطا در به‌روزرسانی تعداد آیتم');
    }
}

// به‌روزرسانی اطلاعات مشتری
async function updateTakeawayCustomer() {
    if (!currentTakeawayId) return Promise.resolve();
    
    const customerName = document.getElementById('takeaway-customer-name').value;
    const customerPhone = document.getElementById('takeaway-customer-phone').value;
    const birthDateInput = document.getElementById('takeaway-customer-birth-date');
    const birthDate = birthDateInput && birthDateInput.value ? birthDateInput.value : null;
    const discountAmount = parseInt(document.getElementById('takeaway-discount-amount').value) || 0;
    const discountPercent = parseFloat(document.getElementById('takeaway-discount-percent').value) || 0;
    
    // محاسبه مجموع تخفیف برای backward compatibility
    const total = takeawayItems.reduce((sum, item) => sum + item.total_price, 0);
    const discountFromPercent = Math.floor(total * discountPercent / 100);
    const totalDiscount = discountAmount + discountFromPercent;
    
    try {
        const response = await fetch(`/takeaway/${currentTakeawayId}/update`, {
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
            updateTakeawayTotals();
            // بارگذاری مجدد داده‌ها از سرور برای اطمینان از همگام‌سازی
            await loadTakeawayData(currentTakeawayId);
            updateTakeawayCard(currentTakeawayId);
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

// ثبت یا به‌روزرسانی سفارش
async function submitTakeawayOrder(orderId) {
    // بررسی اینکه آیا آیتمی در سفارش وجود دارد
    if (takeawayItems.length === 0) {
        alert('لطفاً حداقل یک آیتم انتخاب کنید');
        return;
    }
    
    // ابتدا به‌روزرسانی اطلاعات مشتری و تخفیف
    try {
        await updateTakeawayCustomer();
    } catch (error) {
        console.error('خطا در به‌روزرسانی اطلاعات مشتری:', error);
        // ادامه می‌دهیم حتی اگر به‌روزرسانی مشتری با خطا مواجه شود
    }
    
    try {
        // دریافت اطلاعات مشتری و تخفیف برای ارسال به سرور
        const customerName = document.getElementById('takeaway-customer-name').value;
        const customerPhone = document.getElementById('takeaway-customer-phone').value;
        const discountAmount = parseInt(document.getElementById('takeaway-discount-amount').value) || 0;
        const discountPercent = parseFloat(document.getElementById('takeaway-discount-percent').value) || 0;
        
        // محاسبه مجموع تخفیف
        const total = takeawayItems.reduce((sum, item) => sum + item.total_price, 0);
        const discountFromPercent = Math.floor(total * discountPercent / 100);
        const totalDiscount = discountAmount + discountFromPercent;
        
        const response = await fetch(`/takeaway/${orderId}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: customerName,
                customer_phone: customerPhone,
                discount: totalDiscount,
                discount_amount: discountAmount,
                discount_percent: discountPercent
            })
        });
        
        const data = await response.json();
        if (data.success) {
            const message = currentTakeawayStatus && currentTakeawayStatus !== 'پرداخت شده' 
                ? `سفارش با شماره فاکتور ${data.invoice_number} با موفقیت به‌روزرسانی شد`
                : `سفارش با شماره فاکتور ${data.invoice_number} با موفقیت ثبت شد`;
            alert(message);
            
            // به‌روزرسانی کارت سفارش
            await updateTakeawayCard(orderId);
            
            // بستن modal و reload صفحه
            closeTakeawayModal();
            location.reload();
        } else {
            alert(data.message || 'خطا در ثبت/به‌روزرسانی سفارش');
        }
    } catch (error) {
        console.error('خطا در ثبت/به‌روزرسانی سفارش:', error);
        alert('خطا در ثبت/به‌روزرسانی سفارش');
    }
}

// نمایش/مخفی کردن گزینه‌های پرداخت برای سفارش بیرون‌بر (در کارت‌ها)
function toggleTakeawayCheckoutOptions(orderId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const target = document.getElementById(`takeaway-checkout-options-${orderId}`);
    if (!target) return;
    const isActive = target.classList.contains('active');
    document.querySelectorAll('.takeaway-order-checkout-options').forEach(opt => opt.classList.remove('active'));
    if (!isActive) {
        target.classList.add('active');
    }
}

// نمایش/مخفی کردن گزینه‌های پرداخت در modal
function toggleTakeawayModalCheckoutOptions() {
    const target = document.getElementById('takeaway-modal-checkout-options');
    if (!target) return;
    const isActive = target.classList.contains('active');
    document.querySelectorAll('.takeaway-order-checkout-options').forEach(opt => opt.classList.remove('active'));
    if (!isActive) {
        target.classList.add('active');
    }
}

// تسویه سفارش از modal
function checkoutTakeawayOrderFromModal(paymentMethod) {
    if (currentTakeawayId) {
        checkoutTakeawayOrder(currentTakeawayId, null, paymentMethod);
    }
}

// بستن dropdown هنگام کلیک خارج از آن
document.addEventListener('click', function(e) {
    if (!e.target.closest('.takeaway-order-checkout')) {
        document.querySelectorAll('.takeaway-order-checkout-options').forEach(opt => opt.classList.remove('active'));
    }
});

// تسویه سفارش
async function checkoutTakeawayOrder(orderId, event, paymentMethod = 'کارتخوان') {
    if (event) {
        event.stopPropagation(); // جلوگیری از باز شدن modal
        event.preventDefault(); // جلوگیری از رفتار پیش‌فرض
    }
    
    // بستن dropdown
    document.querySelectorAll('.takeaway-order-checkout-options').forEach(opt => opt.classList.remove('active'));
    
    try {
        const response = await fetch(`/takeaway/${orderId}/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                payment_method: paymentMethod
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`سفارش با موفقیت تسویه شد. شماره فاکتور: ${data.invoice_number}`);
            if (currentTakeawayId === orderId) {
                closeTakeawayModal();
            }
            location.reload();
        } else {
            alert(data.message || 'خطا در تسویه سفارش');
        }
    } catch (error) {
        console.error('خطا در تسویه سفارش:', error);
        alert('خطا در تسویه سفارش');
    }
}

// حذف سفارش بیرون‌بر
async function deleteTakeawayOrder(orderId, event) {
    if (event) {
        event.stopPropagation(); // جلوگیری از باز شدن modal
        event.preventDefault(); // جلوگیری از رفتار پیش‌فرض
    }
    
    try {
        console.log('Deleting takeaway order:', orderId);
        const response = await fetch(`/takeaway/${orderId}/delete`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('خطای HTTP:', response.status, errorText);
            let errorMessage = `خطای سرور: ${response.status}`;
            try {
                const errorData = JSON.parse(errorText);
                if (errorData.message) {
                    errorMessage = errorData.message;
                }
            } catch (e) {
                // اگر نتوانستیم JSON parse کنیم، از errorText استفاده می‌کنیم
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        console.log('Delete response:', data);
        
        if (data.success) {
            alert('سفارش با موفقیت حذف شد');
            // حذف کارت سفارش از داشبورد
            const card = document.querySelector(`.takeaway-order-card[data-order-id="${orderId}"]`);
            if (card) {
                card.remove();
            }
            // برای هماهنگی خلاصه‌های مالی، صفحه را تازه‌سازی می‌کنیم
            window.location.reload();
        } else {
            alert(data.message || 'خطا در حذف سفارش');
        }
    } catch (error) {
        console.error('خطا در حذف سفارش:', error);
        if (error.message === 'Failed to fetch') {
            alert('خطا در اتصال به سرور. لطفاً اطمینان حاصل کنید که سرور در حال اجرا است.');
        } else {
            alert('خطا در حذف سفارش: ' + error.message);
        }
    }
}

// به‌روزرسانی مبلغ کل
// این تابع دیگر استفاده نمی‌شود - مقادیر مستقیماً از سرور خوانده می‌شوند
function updateTakeawayTotals() {
    try {
        // این تابع برای سازگاری با کدهای قدیمی نگه داشته شده است
        // اما مقادیر واقعی از loadTakeawayData تنظیم می‌شوند
        if (takeawayItems.length > 0 && currentTakeawayId) {
            // فقط برای حالت‌های خاص که داده از سرور در دسترس نیست
            const total = takeawayItems.reduce((sum, item) => sum + item.total_price, 0);
            
            // محاسبه تخفیف درصدی (ابتدا)
            const discountPercentEl = document.getElementById('takeaway-discount-percent');
            const discountAmountEl = document.getElementById('takeaway-discount-amount');
            
            if (!discountPercentEl || !discountAmountEl) {
                if (window.debug) window.debug.warn('Takeaway Totals', 'Discount input elements not found');
                return;
            }
            
            const discountPercent = parseFloat(discountPercentEl.value) || 0;
            const discountFromPercent = Math.floor(total * discountPercent / 100);
            
            // محاسبه تخفیف عددی (بعد از درصدی)
            const discountAmount = parseInt(discountAmountEl.value) || 0;
            
            // مجموع تخفیف‌ها
            const totalDiscount = discountFromPercent + discountAmount;
            
            if (window.debug) {
                window.debug.log('Takeaway Totals', 'Calculating totals', {
                    total,
                    discountPercent,
                    discountFromPercent,
                    discountAmount,
                    totalDiscount
                });
            }
            
            const taxPercent = 12; // می‌توان از تنظیمات خواند
            const tax = Math.floor((total - totalDiscount) * taxPercent / 100);
            const final = total - totalDiscount + tax;
            
            const totalAmountEl = document.getElementById('takeaway-total-amount');
            const taxAmountEl = document.getElementById('takeaway-tax-amount');
            const finalAmountEl = document.getElementById('takeaway-final-amount');
            
            if (!totalAmountEl || !taxAmountEl || !finalAmountEl) {
                if (window.debug) window.debug.error('Takeaway Totals', 'Summary elements not found');
                return;
            }
            
            totalAmountEl.textContent = total.toLocaleString();
            taxAmountEl.textContent = tax.toLocaleString();
            finalAmountEl.textContent = final.toLocaleString();
            
            // نمایش تخفیف در summary
            const discountRow = document.getElementById('takeaway-discount-row');
            const discountDisplay = document.getElementById('takeaway-discount-display');
            
            if (!discountRow || !discountDisplay) {
                if (window.debug) window.debug.warn('Takeaway Totals', 'Discount display elements not found');
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
                    window.debug.success('Takeaway Totals', 'Discount displayed', { discountText, totalDiscount });
                }
            } else {
                discountRow.style.display = 'none';
            }
        } else {
            const totalAmountEl = document.getElementById('takeaway-total-amount');
            const taxAmountEl = document.getElementById('takeaway-tax-amount');
            const finalAmountEl = document.getElementById('takeaway-final-amount');
            
            if (totalAmountEl) totalAmountEl.textContent = '0';
            if (taxAmountEl) taxAmountEl.textContent = '0';
            if (finalAmountEl) finalAmountEl.textContent = '0';
            
            // مخفی کردن ردیف تخفیف
            const discountRow = document.getElementById('takeaway-discount-row');
            if (discountRow) {
                discountRow.style.display = 'none';
            }
        }
    } catch (error) {
        if (window.debug) {
            window.debug.error('Takeaway Totals', 'Error in updateTakeawayTotals', {
                error: error.message,
                stack: error.stack
            });
        }
        console.error('Error in updateTakeawayTotals:', error);
    }
}

// به‌روزرسانی کارت سفارش
async function updateTakeawayCard(orderId) {
    try {
        // دریافت اطلاعات به‌روزرسانی شده سفارش از سرور
        const response = await fetch(`/takeaway/${orderId}`);
        if (!response.ok) {
            console.error('خطا در دریافت اطلاعات سفارش');
            return;
        }
        
        const data = await response.json();
        if (!data.id) {
            console.error('سفارش یافت نشد');
            return;
        }
        
        // پیدا کردن کارت سفارش در DOM
        const card = document.querySelector(`.takeaway-order-card[data-order-id="${orderId}"]`);
        if (!card) {
            console.warn('کارت سفارش در داشبورد یافت نشد؛ برای دیدن وضعیت جدید صفحه را دستی تازه کنید.');
            return;
        }
        
        // به‌روزرسانی مبلغ
        const amountElement = card.querySelector('.takeaway-amount');
        if (amountElement) {
            const finalAmount = data.final_amount || 0;
            amountElement.textContent = `${finalAmount.toLocaleString('fa-IR')}`;
        }
        
        // به‌روزرسانی نام مشتری
        const customerElement = card.querySelector('.takeaway-customer');
        if (customerElement) {
            customerElement.textContent = data.customer_name || 'مشتری ناشناس';
        }
        
        // به‌روزرسانی وضعیت (اگر تغییر کرده باشد)
        const statusElement = card.querySelector('.takeaway-status');
        if (statusElement) {
            statusElement.textContent = data.status || 'پرداخت نشده';
            statusElement.className = `takeaway-status ${data.status === 'پرداخت شده' ? 'paid' : 'unpaid'}`;
        }
        
        // اگر سفارش پرداخت شده، دکمه‌های ثبت و تسویه را حذف کن
        if (data.status === 'پرداخت شده') {
            const actionsDiv = card.querySelector('.takeaway-order-actions');
            if (actionsDiv) {
                actionsDiv.innerHTML = '<button class="btn-edit-takeaway" onclick="openTakeawayModal(' + orderId + ', event)">ویرایش</button>';
            }
        }
        
    } catch (error) {
        console.error('خطا در به‌روزرسانی کارت سفارش:', error);
    }
}

// پاک کردن فرم
function clearTakeawayForm() {
    document.getElementById('takeaway-customer-name').value = '';
    document.getElementById('takeaway-customer-phone').value = '';
    document.getElementById('takeaway-discount').value = '0';
    document.getElementById('takeaway-items-list').innerHTML = '<p class="empty-message">هیچ آیتمی انتخاب نشده است</p>';
    
    // فعال کردن دکمه اعمال تخفیف
    const applyDiscountBtn = document.getElementById('apply-takeaway-discount');
    if (applyDiscountBtn) {
        applyDiscountBtn.disabled = false;
        applyDiscountBtn.style.opacity = '1';
        applyDiscountBtn.style.cursor = 'pointer';
        applyDiscountBtn.title = 'اعمال تخفیف';
        applyDiscountBtn.textContent = '✓';
        applyDiscountBtn.style.background = '';
    }
    
    updateTakeawayTotals();
}

// فیلتر کردن آیتم‌های منو
function filterTakeawayMenuItems() {
    const searchTerm = document.getElementById('takeaway-menu-search-input').value.toLowerCase();
    const menuItems = document.querySelectorAll('#takeaway-modal .menu-item-selectable');
    
    menuItems.forEach(item => {
        const itemName = item.getAttribute('data-item-name').toLowerCase();
        if (itemName.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// رویدادهای کلیک
document.addEventListener('DOMContentLoaded', function() {
    // Event delegation برای آیتم‌های منو در modal سفارشات بیرون‌بر (fallback)
    // این فقط به عنوان fallback استفاده می‌شود، event listener مستقیم اولویت دارد
    document.addEventListener('click', function(e) {
        // بررسی اینکه آیا کلیک روی آیتم منو در modal سفارشات بیرون‌بر است
        const menuItem = e.target.closest('#takeaway-modal .menu-item-selectable');
        if (menuItem) {
            // بررسی اینکه modal باز است
            const modal = document.getElementById('takeaway-modal');
            if (modal && modal.style.display === 'flex' && currentTakeawayId) {
                // فقط اگر event هنوز stop نشده باشد (fallback)
                e.stopPropagation(); // جلوگیری از انتشار event به modal
                e.preventDefault(); // جلوگیری از رفتار پیش‌فرض
                e.stopImmediatePropagation(); // جلوگیری از اجرای سایر listener ها
                const itemId = parseInt(menuItem.getAttribute('data-item-id'));
                if (itemId && !isNaN(itemId)) {
                    console.log('Adding item to takeaway (delegation fallback):', itemId);
                    addItemToTakeaway(itemId);
                }
                return false;
            }
        }
    }, true); // استفاده از capture phase
    
    // به‌روزرسانی خودکار اطلاعات مشتری
    const customerNameInput = document.getElementById('takeaway-customer-name');
    const customerPhoneInput = document.getElementById('takeaway-customer-phone');
    const discountAmountInput = document.getElementById('takeaway-discount-amount');
    const discountPercentInput = document.getElementById('takeaway-discount-percent');
    
    if (customerNameInput) {
        customerNameInput.addEventListener('blur', updateTakeawayCustomer);
    }
    if (customerPhoneInput) {
        customerPhoneInput.addEventListener('blur', updateTakeawayCustomer);
    }
    if (discountAmountInput) {
        discountAmountInput.addEventListener('input', function() {
            // به‌روزرسانی محاسبات به صورت real-time
            updateTakeawayTotals();
        });
        
        discountAmountInput.addEventListener('blur', function() {
            // ذخیره در دیتابیس
            updateTakeawayCustomer();
        });
    }
    if (discountPercentInput) {
        discountPercentInput.addEventListener('input', function() {
            // به‌روزرسانی محاسبات به صورت real-time
            updateTakeawayTotals();
        });
        
        discountPercentInput.addEventListener('blur', function() {
            // ذخیره در دیتابیس
            updateTakeawayCustomer();
        });
    }
    
    // Event delegation برای دکمه‌های کنترل تعداد و حذف در جدول آیتم‌ها
    document.addEventListener('click', function(e) {
        const takeawayModal = document.getElementById('takeaway-modal');
        if (!takeawayModal || takeawayModal.style.display !== 'flex') {
            return;
        }
        
        // بررسی کلیک روی دکمه اعمال تخفیف عددی
        const applyDiscountAmountBtn = e.target.closest('#apply-takeaway-discount-amount') || (e.target.id === 'apply-takeaway-discount-amount' ? e.target : null);
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
            updateTakeawayTotals();
            
            // ارسال به سرور
            updateTakeawayCustomer().then(() => {
                console.log('تخفیف عددی با موفقیت اعمال شد');
                // نمایش بازخورد بصری
                applyDiscountAmountBtn.textContent = '✓';
                applyDiscountAmountBtn.style.background = 'var(--color-success)';
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
        const applyDiscountPercentBtn = e.target.closest('#apply-takeaway-discount-percent') || (e.target.id === 'apply-takeaway-discount-percent' ? e.target : null);
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
            updateTakeawayTotals();
            
            // ارسال به سرور
            updateTakeawayCustomer().then(() => {
                console.log('تخفیف درصدی با موفقیت اعمال شد');
                // نمایش بازخورد بصری
                applyDiscountPercentBtn.textContent = '✓';
                applyDiscountPercentBtn.style.background = 'var(--color-success)';
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
        
        // بررسی کلیک روی دکمه‌های کنترل تعداد یا حذف
        const button = e.target.closest('#takeaway-modal .btn-quantity, #takeaway-modal .btn-remove');
        if (button) {
            e.preventDefault();
            e.stopPropagation();
            const itemId = parseInt(button.getAttribute('data-item-id'));
            const action = button.getAttribute('data-action');
            
            if (itemId && !isNaN(itemId) && currentTakeawayId) {
                if (action === 'increase') {
                    increaseTakeawayItemQuantity(itemId);
                } else if (action === 'decrease') {
                    decreaseTakeawayItemQuantity(itemId);
                } else if (action === 'remove') {
                    showTakeawayRemoveReasonField(itemId);
                }
            }
            return false;
        }
        
        // بررسی کلیک روی دکمه تأیید حذف
        const confirmDeleteBtn = e.target.closest('#takeaway-modal button[data-action="confirm-delete"]');
        if (confirmDeleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const itemId = parseInt(confirmDeleteBtn.getAttribute('data-item-id'));
            if (itemId && !isNaN(itemId) && currentTakeawayId) {
                confirmRemoveTakeawayItem(itemId);
            }
            return false;
        }
        
        // بررسی کلیک روی دکمه لغو حذف
        const cancelDeleteBtn = e.target.closest('#takeaway-modal button[data-action="cancel-delete"]');
        if (cancelDeleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const itemId = parseInt(cancelDeleteBtn.getAttribute('data-item-id'));
            if (itemId && !isNaN(itemId)) {
                hideTakeawayRemoveReasonField(itemId);
            }
            return false;
        }
        
        // بررسی کلیک روی دکمه ثبت سفارش
        if (e.target && (e.target.id === 'submit-takeaway-order' || e.target.closest('#submit-takeaway-order'))) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Submit takeaway button clicked via delegation!');
            if (currentTakeawayId) {
                submitTakeawayOrder(currentTakeawayId);
            }
            return false;
        }
        
        // بررسی کلیک روی دکمه تسویه سفارش
        if (e.target && (e.target.id === 'checkout-takeaway-order' || e.target.closest('#checkout-takeaway-order'))) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Checkout takeaway button clicked via delegation!');
            if (currentTakeawayId) {
                toggleTakeawayModalCheckoutOptions();
            }
            return false;
        }
    }, true); // استفاده از capture phase
    
    // بستن مودال با کلیک روی پس‌زمینه
    // این event listener باید در سطح document باشد تا با event delegation تداخل نکند
    document.addEventListener('click', function(e) {
        const takeawayModal = document.getElementById('takeaway-modal');
        if (!takeawayModal || takeawayModal.style.display !== 'flex') {
            return; // اگر modal باز نیست، کاری نکن
        }
        
        // فقط اگر روی خود modal background کلیک شده (نه روی محتوای داخل آن)
        if (e.target === takeawayModal) {
            // اگر روی background کلیک شده (نه روی content)، modal را ببند
            closeTakeawayModal();
        }
    }, false); // استفاده از bubble phase نه capture phase
    
    // جلوگیری از بسته شدن modal وقتی روی محتوای آن کلیک می‌شود
    // این باید در capture phase باشد تا قبل از رسیدن به modal background متوقف شود
    document.addEventListener('click', function(e) {
        const takeawayModal = document.getElementById('takeaway-modal');
        if (!takeawayModal || takeawayModal.style.display !== 'flex') {
            return;
        }
        
        const modalContent = takeawayModal.querySelector('.table-modal-content');
        if (modalContent && modalContent.contains(e.target)) {
            // اگر کلیک روی محتوای modal است، از انتشار به background جلوگیری کن
            e.stopPropagation();
        }
    }, true); // استفاده از capture phase
    
    // راه‌اندازی جستجوی مشتری
    initTakeawayCustomerSearch();
});

// اطمینان از اینکه توابع در scope global قرار دارند
window.confirmRemoveTakeawayItem = confirmRemoveTakeawayItem;
window.hideTakeawayRemoveReasonField = hideTakeawayRemoveReasonField;
window.showTakeawayRemoveReasonField = showTakeawayRemoveReasonField;

