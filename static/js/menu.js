document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('menuItemModal');
    const closeModalBtn = modal.querySelector('.close-modal');
    const form = document.getElementById('menu-item-form');
    const itemIdInput = document.getElementById('item-id');
    const itemNameInput = document.getElementById('item-name');
    const itemPriceInput = document.getElementById('item-price');
    const itemStockInput = document.getElementById('item-stock');
    const categoryInput = document.getElementById('item-category');
    const modalTitle = document.getElementById('modal-title');
    const addNewItemBtn = document.getElementById('add-new-menu-item-btn');

    // باز کردن مودال برای افزودن
    if (addNewItemBtn) {
        addNewItemBtn.addEventListener('click', function () {
            form.reset();
            itemIdInput.value = '';
            modalTitle.textContent = 'افزودن آیتم منو';
            modal.style.display = 'block';
        });
    }

    // بستن مودال
    if (closeModalBtn) { // Ensure closeModalBtn exists
        closeModalBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
        const categoryModal = document.getElementById('categoryModal'); // Define categoryModal here if used in this event
        if (event.target === categoryModal) {
            categoryModal.style.display = 'none';
        }
    });

    // ثبت فرم افزودن یا ویرایش (از طریق مودال)
    if (form) { // Ensure form exists
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const payload = {
                id: itemIdInput.value,
                name: itemNameInput.value,
                price: itemPriceInput.value,
                stock: itemStockInput.value,
                category_id: categoryInput.value
            };

            console.log('Sending payload (modal):', payload);

            fetch('/menu/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
                .then(res => {
                    console.log('Response status (modal):', res.status);
                    return res.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        modal.style.display = 'none';
                        location.reload();
                    } else {
                        alert('خطا در ذخیره آیتم: ' + (data.message || ''));
                    }
                })
                .catch(err => {
                    console.error('Error (modal):', err);
                    alert('خطا در ارتباط با سرور');
                });
        });
    }

    // دکمه‌های ✏️ (ویرایش از طریق مودال) - این بخش ممکن است با ویرایش درون‌خطی دیگر لازم نباشد
    // document.querySelectorAll('.edit-btn').forEach(button => {
    //     button.addEventListener('click', function () {
    //         const itemElement = this.closest('.menu-item'); // This would refer to the old structure
    //         const itemId = itemElement.dataset.itemId;
    //         const itemName = itemElement.dataset.itemName;
    //         const itemPrice = itemElement.dataset.itemPrice;
    //         const itemStock = itemElement.dataset.itemStock;
    //         // To get category_id, you'd need to find it, e.g., from a parent or another data attribute
    //         // const itemCategoryId = itemElement.dataset.itemCategoryId; // Assuming it exists

    //         document.getElementById('item-id').value = itemId;
    //         document.getElementById('item-name').value = itemName;
    //         document.getElementById('item-price').value = itemPrice;
    //         document.getElementById('item-stock').value = itemStock;
    //         // document.getElementById('item-category').value = itemCategoryId; // Set category in modal

    //         document.getElementById('modal-title').textContent = 'ویرایش آیتم منو';
    //         document.getElementById('menuItemModal').style.display = 'block';
    //     });
    // });

    // Event delegation برای دکمه‌های حذف آیتم (❌) و سایر عملیات روی .container
    // NOTE: The delete-btn handling is moved to a separate document-level listener below.
    const container = document.querySelector('.container');
    if (container) {
        container.addEventListener('click', function (e) {
            // حذف آیتم منو - HANDLED BY SEPARATE LISTENER BELOW (Removed old commented code)

            // حذف دسته‌بندی
            if (e.target.classList.contains('delete-category-btn')) {
                const categoryId = e.target.dataset.id;
                if (confirm('آیا مطمئن هستید که می‌خواهید این دسته‌بندی حذف شود؟ این عمل تمامی آیتم‌های داخل آن را نیز حذف خواهد کرد.')) {
                    fetch(`/menu/category/delete/${categoryId}`, {
                        method: 'POST' // Or 'DELETE'
                    })
                        .then(res => res.json())
                        .then(data => {
                            if (data.status === 'deleted') {
                                location.reload();
                            } else {
                                alert(data.message || 'خطا در حذف دسته‌بندی');
                            }
                        })
                        .catch(() => alert('خطا در ارتباط با سرور هنگام حذف دسته‌بندی'));
                }
            }
        });
    }


    // --- START: کد جدید برای دکمه‌های ذخیره درون‌خطی ---
    document.querySelectorAll('.inline-save-btn').forEach(button => {
        button.addEventListener('click', function () {
            const itemElement = this.closest('.menu-item');
            const id = itemElement.dataset.itemId; // ID از data-attribute خود آیتم li
            const name = itemElement.querySelector('.inline-name').value;
            const price = itemElement.querySelector('.inline-price').value;
            const stock = itemElement.querySelector('.inline-stock').value;

            // !!! هشدار: category_id به صورت ثابت 1 در نظر گرفته شده است.
            // این باید به صورت داینامیک تعیین شود. برای مثال:
            // const categoryBlock = itemElement.closest('.category-block');
            // const category_id = categoryBlock ? categoryBlock.dataset.categoryId : null;
            // اطمینان حاصل کنید که data-category-id در HTML به .category-block اضافه شده است.
            const category_id_temp = 1; // مقدار موقت، باید اصلاح شود

            const payload = {
                id: id,
                name: name,
                price: price,
                stock: stock,
                category_id: category_id_temp // TODO: این مقدار باید داینامیک باشد
            };

            console.log('Sending payload (inline save):', payload);

            fetch('/menu/save', { // همان اندپوینت ذخیره مودال
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('آیتم با موفقیت به‌روزرسانی شد!');
                        // می‌توانید به جای رفرش کامل صفحه، فقط ظاهر آیتم را به‌روز کنید
                        // یا یک نشانگر موفقیت نمایش دهید.
                        // location.reload(); // برای سادگی فعلا رفرش می‌کنیم
                    } else {
                        alert('خطا در ذخیره آیتم: ' + (data.message || 'نا مشخص'));
                    }
                })
                .catch(err => {
                    console.error('Error saving item inline:', err);
                    alert('خطا در ارتباط با سرور هنگام ذخیره آیتم.');
                });
        });
    });
    // --- END: کد جدید برای دکمه‌های ذخیره درون‌خطی ---


    // دسته‌بندی: باز کردن مودال افزودن دسته‌بندی
    const categoryModal = document.getElementById('categoryModal');
    const addCategoryBtn = document.getElementById('add-new-category-btn');
    const closeCategoryModalBtn = categoryModal ? categoryModal.querySelector('.close-modal') : null;
    const categoryForm = document.getElementById('category-form');

    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => {
            if (categoryForm) categoryForm.reset();
            if (categoryModal) categoryModal.style.display = 'block';
        });
    }

    if (closeCategoryModalBtn) {
        closeCategoryModalBtn.addEventListener('click', () => {
            if (categoryModal) categoryModal.style.display = 'none';
        });
    }

    // Event listener برای بستن مودال دسته‌بندی با کلیک بیرون از آن در window click handler بالا اضافه شد

    if (categoryForm) {
        categoryForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const nameInput = document.getElementById('category-name');
            const descriptionInput = document.getElementById('category-description');

            if (!nameInput || !descriptionInput) {
                alert('خطا: فیلدهای فرم دسته‌بندی یافت نشد.');
                return;
            }

            const name = nameInput.value;
            const description = descriptionInput.value;

            fetch('/menu/category/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, description }) // Assuming id is auto-generated or handled by backend for new
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('دسته‌بندی جدید اضافه شد!');
                        location.reload();
                    } else {
                        alert(data.message || 'خطا در ذخیره دسته‌بندی');
                    }
                })
                .catch(() => alert('خطا در ارسال درخواست برای ذخیره دسته‌بندی'));
        });
    }
});

// حذف آیتم منو بدون مدال (استفاده از Event Delegation در سطح document)
// NOTE: This is the ONLY delete-btn handler kept
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('delete-btn')) {
        const itemId = e.target.getAttribute('data-id');
        if (!itemId) return;
        if (confirm('آیا مطمئن هستید که می‌خواهید این آیتم را حذف کنید؟')) {
            fetch(`/menu/item/delete/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({})
            })
                .then(async response => {
                    const contentType = response.headers.get('content-type');
                    const data = (contentType && contentType.includes('application/json'))
                        ? await response.json().catch(() => ({}))
                        : {};

                    if (!response.ok) {
                        const message = data.message || `HTTP error! status: ${response.status}`;
                        throw new Error(message);
                    }

                    return data;
                })
                .then(data => {
                    // Assuming backend returns { success: true } or { success: false, message: '...' }
                    // Or if the non-JSON case returns {}, assume success if response.ok was true
                    if (data.success || Object.keys(data).length === 0) { // Check for success: true or empty object for non-JSON OK response
                        const item = e.target.closest('.menu-item');
                        if (item) item.remove();
                    } else {
                        // If status was OK but data.success is false
                        alert('خطا در حذف آیتم' + (data.message ? ': ' + data.message : ''));
                    }
                })
                .catch(err => {
                    console.error('حذف آیتم با خطا مواجه شد:', err);
                    // Display a more informative error message
                    alert('خطا در ارتباط با سرور یا پردازش پاسخ: ' + err.message);
                });
        }
    }
});
