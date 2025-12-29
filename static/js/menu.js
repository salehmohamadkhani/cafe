document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('menuItemModal');
    const closeModalBtn = modal.querySelector('.close-modal');
    const form = document.getElementById('menu-item-form');
    const itemIdInput = document.getElementById('item-id');
    const itemNameInput = document.getElementById('item-name');
    const itemPriceInput = document.getElementById('item-price');
    const itemStockInput = document.getElementById('item-stock');
    const modalTitle = document.getElementById('modal-title');
    const addNewItemBtn = document.getElementById('add-new-menu-item-btn');
    const materialsModal = document.getElementById('materialsModal');
    const closeMaterialsModalBtn = document.getElementById('close-materials-modal');
    const materialsModalTitle = document.getElementById('materials-modal-title');
    const materialsListEl = document.getElementById('materials-list');
    const materialsForm = document.getElementById('materials-form');
    const materialNameInput = document.getElementById('material-name');
    const materialQuantityInput = document.getElementById('material-quantity');
    const materialRawInput = document.getElementById('material-raw-input');
    const materialRawDropdown = document.getElementById('material-raw-dropdown');
    const materialRawAutocomplete = document.getElementById('material-raw-autocomplete');
    const materialRawIdInput = document.getElementById('material-raw-id');
    const materialPreProductionInput = document.getElementById('material-pre-production-input');
    const materialPreProductionDropdown = document.getElementById('material-pre-production-dropdown');
    const materialPreProductionAutocomplete = document.getElementById('material-pre-production-autocomplete');
    const materialPreProductionIdInput = document.getElementById('material-pre-production-id');
    const materialUnitBadge = document.getElementById('material-unit-badge');
    const materialsSummaryCount = document.getElementById('materials-summary-count');
    let activeMaterialsItemId = null;
    let rawMaterialsCache = [];
    let preProductionItemsCache = [];
    let availableRawMaterials = [];
    let rawDropdownActiveIndex = -1;
    let rawDropdownItems = [];
    let preProductionDropdownActiveIndex = -1;
    let preProductionDropdownItems = [];

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
        if (materialsModal && event.target === materialsModal) {
            closeMaterialsModal();
        }
    });

    // ثبت فرم افزودن یا ویرایش (از طریق مودال)
    if (form) { // Ensure form exists
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const categorySelect = document.getElementById('item-category');
            const payload = {
                id: itemIdInput.value,
                name: itemNameInput.value,
                price: itemPriceInput.value,
                stock: itemStockInput.value,
                category_id: categorySelect ? (categorySelect.value || null) : null
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
                        // اگر در iframe هستیم، فقط iframe را reload کنیم
                        if (window.self !== window.top) {
                            // در iframe هستیم
                            location.reload();
                        } else {
                            // در صفحه اصلی هستیم
                            location.reload();
                        }
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



    // --- START: کد جدید برای دکمه‌های ذخیره درون‌خطی ---
    // استفاده از event delegation برای دکمه‌های ذخیره
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('materials-btn') || e.target.closest('.materials-btn')) {
            const button = e.target.classList.contains('materials-btn') ? e.target : e.target.closest('.materials-btn');
            const itemElement = button.closest('.menu-item');
            if (!itemElement) return;
            const itemId = parseInt(itemElement.dataset.itemId);
            const itemNameInputEl = itemElement.querySelector('.inline-name');
            const itemName = itemNameInputEl ? itemNameInputEl.value : '';
            openMaterialsModal(itemId, itemName);
            return;
        }

        if (e.target.classList.contains('inline-save-btn') || e.target.closest('.inline-save-btn')) {
            const button = e.target.classList.contains('inline-save-btn') ? e.target : e.target.closest('.inline-save-btn');
            const itemElement = button.closest('.menu-item');
            if (!itemElement) return;
            
            const id = itemElement.dataset.itemId;
            const name = itemElement.querySelector('.inline-name').value;
            const price = itemElement.querySelector('.inline-price').value;
            const stock = itemElement.querySelector('.inline-stock').value;

            const payload = {
                id: id,
                name: name,
                price: price,
                stock: stock
            };

            console.log('Sending payload (inline save):', payload);

            fetch('/menu/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        // اگر در iframe هستیم، به parent window پیام بدهیم
                        if (window.self !== window.top) {
                            // در iframe هستیم - به parent window پیام بدهیم
                            window.parent.postMessage({type: 'menuUpdated', itemId: id}, '*');
                        }
                        // Refresh menu in modals if they are open
                        if (typeof refreshMenuInModals === 'function') {
                            refreshMenuInModals();
                        }
                        alert('آیتم با موفقیت به‌روزرسانی شد!');
                    } else {
                        alert('خطا در ذخیره آیتم: ' + (data.message || 'نامشخص'));
                    }
                })
                .catch(err => {
                    console.error('Error saving item inline:', err);
                    alert('خطا در ارتباط با سرور هنگام ذخیره آیتم.');
                });
        }
    });
    // --- END: کد جدید برای دکمه‌های ذخیره درون‌خطی ---



    if (closeMaterialsModalBtn) {
        closeMaterialsModalBtn.addEventListener('click', closeMaterialsModal);
    }

    if (materialsForm) {
        materialsForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!activeMaterialsItemId) {
                alert('لطفاً ابتدا یک آیتم را انتخاب کنید.');
                return;
            }

            const rawMaterialId = materialRawIdInput ? materialRawIdInput.value : '';
            const preProductionItemId = materialPreProductionIdInput ? materialPreProductionIdInput.value : '';
            
            if (!rawMaterialId && !preProductionItemId) {
                alert('لطفاً ماده اولیه یا محصول پیش تولید را انتخاب کنید.');
                return;
            }

            let name = '';
            let unit = 'عدد';
            let payload = {};

            if (rawMaterialId) {
                const selectedMaterial = rawMaterialsCache.find(rm => String(rm.id) === String(rawMaterialId));
                if (!selectedMaterial) {
                    alert('لطفاً ماده اولیه معتبری را انتخاب کنید.');
                    if (materialRawInput) materialRawInput.focus();
                    return;
                }
                name = selectedMaterial.name.trim();
                unit = selectedMaterial.default_unit || 'عدد';
                payload = {
                    name,
                    quantity: materialQuantityInput.value.trim(),
                    unit: unit,
                    raw_material_id: parseInt(selectedMaterial.id, 10)
                };
            } else if (preProductionItemId) {
                const selectedItem = preProductionItemsCache.find(item => String(item.id) === String(preProductionItemId));
                if (!selectedItem) {
                    alert('لطفاً محصول پیش تولید معتبری را انتخاب کنید.');
                    if (materialPreProductionInput) materialPreProductionInput.focus();
                    return;
                }
                name = selectedItem.name.trim();
                unit = selectedItem.unit || 'عدد';
                payload = {
                    name,
                    quantity: materialQuantityInput.value.trim(),
                    unit: unit,
                    pre_production_item_id: parseInt(selectedItem.id, 10)
                };
            }

            const quantity = materialQuantityInput.value.trim();
            if (!name || !quantity) {
                alert('لطفاً ماده اولیه یا محصول پیش تولید و مقدار مصرف را مشخص کنید.');
                return;
            }

            if (materialNameInput) {
                materialNameInput.value = name;
            }

            if (materialUnitBadge) {
                materialUnitBadge.textContent = unit;
            }

            fetch(`/menu/item/${activeMaterialsItemId}/materials`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        if (materialQuantityInput) {
                            materialQuantityInput.value = '';
                            materialQuantityInput.focus();
                        }
                        if (materialRawInput) {
                            materialRawInput.value = '';
                        }
                        if (materialRawIdInput) {
                            materialRawIdInput.value = '';
                        }
                        if (materialPreProductionInput) {
                            materialPreProductionInput.value = '';
                        }
                        if (materialPreProductionIdInput) {
                            materialPreProductionIdInput.value = '';
                        }
                        if (materialNameInput) {
                            materialNameInput.value = '';
                        }
                        if (materialUnitBadge) {
                            materialUnitBadge.textContent = '-';
                        }
                        loadMaterialsList(activeMaterialsItemId);
                    } else {
                        alert(data.message || 'خطا در ثبت متریال.');
                    }
                })
                .catch(error => {
                    console.error('Error saving material:', error);
                    alert('خطا در ارتباط با سرور هنگام ثبت متریال.');
                });
        });
    }

    if (materialsListEl) {
        materialsListEl.addEventListener('click', function (e) {
            if (e.target.classList.contains('material-delete-btn')) {
                const materialId = e.target.getAttribute('data-material-id');
                if (!materialId || !activeMaterialsItemId) return;

                fetch(`/menu/item/${activeMaterialsItemId}/materials/${materialId}`, {
                    method: 'DELETE'
                })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            loadMaterialsList(activeMaterialsItemId);
                        } else {
                            alert(data.message || 'خطا در حذف متریال.');
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting material:', error);
                        alert('خطا در ارتباط با سرور هنگام حذف متریال.');
                    });
            }
        });
    }

    function openMaterialsModal(itemId, itemName) {
        if (!materialsModal) return;
        activeMaterialsItemId = itemId;
        if (materialsModalTitle) {
            materialsModalTitle.textContent = itemName ? `متریال مصرفی - ${itemName}` : 'متریال مصرفی';
        }
        materialsModal.style.display = 'block';
        loadMaterialsList(itemId);
    }

    function closeMaterialsModal() {
        if (materialsModal) {
            materialsModal.style.display = 'none';
        }
        activeMaterialsItemId = null;
        if (materialsListEl) {
            materialsListEl.innerHTML = 'متریالی ثبت نشده است.';
            materialsListEl.classList.add('empty');
        }
        // مخفی کردن جمع کل
        const materialsTotal = document.getElementById('materials-total');
        if (materialsTotal) {
            materialsTotal.style.display = 'none';
        }
        if (materialsSummaryCount) {
            materialsSummaryCount.textContent = '۰';
        }
        if (materialsForm) {
            materialsForm.reset();
        }
        if (materialUnitBadge) {
            materialUnitBadge.textContent = 'عدد';
        }
        if (materialRawInput) {
            materialRawInput.value = '';
        }
        if (materialRawIdInput) {
            materialRawIdInput.value = '';
        }
        if (materialNameInput) {
            materialNameInput.value = '';
        }
    }

    function loadMaterialsList(itemId) {
        if (!materialsListEl) return;
        materialsListEl.classList.remove('empty');
        materialsListEl.innerHTML = '<div style="text-align:center; padding:1rem;">در حال بارگذاری...</div>';

        fetch(`/menu/item/${itemId}/materials`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    if (data.raw_materials) {
                        setRawMaterialOptions(data.raw_materials);
                    }
                    if (data.pre_production_items) {
                        preProductionItemsCache = Array.isArray(data.pre_production_items) ? data.pre_production_items : [];
                    }
                    renderMaterialsList(data.materials || []);
                } else {
                    materialsListEl.classList.add('empty');
                    materialsListEl.innerHTML = data.message || 'خطا در دریافت متریال‌ها.';
                }
            })
            .catch(error => {
                console.error('Error loading materials:', error);
                materialsListEl.classList.add('empty');
                materialsListEl.innerHTML = 'خطا در دریافت متریال‌ها.';
            });
    }

    function setRawMaterialOptions(rawMaterials) {
        rawMaterialsCache = Array.isArray(rawMaterials) ? rawMaterials : [];
        renderRawDropdown('');
        closeRawDropdown();
        if (materialRawInput) {
            materialRawInput.value = '';
        }
        if (materialRawIdInput) {
            materialRawIdInput.value = '';
        }
        if (materialNameInput) {
            materialNameInput.value = '';
        }
        if (materialUnitBadge) {
            materialUnitBadge.textContent = '-';
        }
    }

    function openRawDropdown() {
        if (!materialRawDropdown) return;
        if (!rawDropdownItems || rawDropdownItems.length === 0) return;
        materialRawDropdown.style.display = 'block';
    }

    function closeRawDropdown() {
        if (!materialRawDropdown) return;
        materialRawDropdown.style.display = 'none';
        rawDropdownActiveIndex = -1;
        updateRawDropdownActive();
    }

    function isRawDropdownOpen() {
        return !!(materialRawDropdown && materialRawDropdown.style.display !== 'none');
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function renderRawDropdown(query) {
        if (!materialRawDropdown) return;
        const q = (query || '').trim().toLowerCase();
        const filtered = rawMaterialsCache
            .filter(rm => (rm && rm.name ? String(rm.name).toLowerCase().includes(q) : false))
            .slice(0, 40);

        rawDropdownItems = filtered;
        rawDropdownActiveIndex = filtered.length ? 0 : -1;

        if (!filtered.length) {
            materialRawDropdown.innerHTML = `<div class="ds-autocomplete__empty">موردی یافت نشد</div>`;
            return;
        }

        materialRawDropdown.innerHTML = filtered.map((rm, idx) => {
            const name = escapeHtml(rm.name || '');
            const unit = escapeHtml(rm.default_unit_display || rm.default_unit || '');
            const id = escapeHtml(rm.id);
            return `
                <div class="ds-autocomplete__option${idx === 0 ? ' active' : ''}" role="option"
                     data-id="${id}" data-name="${name}">
                    <strong>${name}</strong>
                    <span>${unit}</span>
                </div>
            `;
        }).join('');
    }

    function updateRawDropdownActive() {
        if (!materialRawDropdown) return;
        const options = materialRawDropdown.querySelectorAll('.ds-autocomplete__option');
        options.forEach((el, idx) => {
            if (idx === rawDropdownActiveIndex) el.classList.add('active');
            else el.classList.remove('active');
        });
    }

    function selectRawMaterialById(id) {
        const match = rawMaterialsCache.find(rm => String(rm.id) === String(id));
        if (!match) return;
        if (materialRawInput) materialRawInput.value = match.name || '';
        if (materialRawIdInput) materialRawIdInput.value = match.id;
        if (materialNameInput) materialNameInput.value = match.name || '';
        if (materialUnitBadge) materialUnitBadge.textContent = match.default_unit_display || match.default_unit || '-';
        closeRawDropdown();
    }

    function syncRawMaterialSelection() {
        if (!materialRawInput) return;
        const value = materialRawInput.value.trim().toLowerCase();
        let match = rawMaterialsCache.find(rm => (rm.name || '').toLowerCase() === value);

        if (!match && value.length > 0) {
            const partialMatches = rawMaterialsCache.filter(rm => (rm.name || '').toLowerCase().includes(value));
            if (partialMatches.length === 1) {
                match = partialMatches[0];
                if (materialRawInput) {
                    materialRawInput.value = partialMatches[0].name || '';
                }
            }
        }

        if (match) {
            if (materialRawIdInput) {
                materialRawIdInput.value = match.id;
            }
            if (materialNameInput) {
                materialNameInput.value = match.name;
            }
            if (materialUnitBadge) {
                materialUnitBadge.textContent = match.default_unit_display || match.default_unit || '-';
            }
        } else {
            if (materialRawIdInput) {
                materialRawIdInput.value = '';
            }
            if (materialNameInput) {
                materialNameInput.value = '';
            }
            if (materialUnitBadge) {
                materialUnitBadge.textContent = '-';
            }
        }
    }

    if (materialRawInput) {
        materialRawInput.addEventListener('focus', function () {
            renderRawDropdown(materialRawInput.value);
            openRawDropdown();
        });
        materialRawInput.addEventListener('input', function () {
            renderRawDropdown(materialRawInput.value);
            openRawDropdown();
            syncRawMaterialSelection();
        });
        materialRawInput.addEventListener('change', syncRawMaterialSelection);
        materialRawInput.addEventListener('keydown', function (e) {
            if (!rawDropdownItems || rawDropdownItems.length === 0) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!isRawDropdownOpen()) openRawDropdown();
                rawDropdownActiveIndex = Math.min(rawDropdownActiveIndex + 1, rawDropdownItems.length - 1);
                updateRawDropdownActive();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!isRawDropdownOpen()) openRawDropdown();
                rawDropdownActiveIndex = Math.max(rawDropdownActiveIndex - 1, 0);
                updateRawDropdownActive();
            } else if (e.key === 'Enter') {
                if (!isRawDropdownOpen()) return;
                e.preventDefault();
                const current = rawDropdownItems[rawDropdownActiveIndex];
                if (current && current.id != null) {
                    selectRawMaterialById(current.id);
                }
            } else if (e.key === 'Escape') {
                closeRawDropdown();
            }
        });
    }

    if (materialRawDropdown) {
        materialRawDropdown.addEventListener('click', function (e) {
            const option = e.target.closest('.ds-autocomplete__option');
            if (!option) return;
            const id = option.getAttribute('data-id');
            if (id) {
                selectRawMaterialById(id);
            }
        });
    }

    document.addEventListener('click', function (e) {
        if (!materialRawAutocomplete || !materialRawDropdown) return;
        if (materialRawAutocomplete.contains(e.target)) return;
        closeRawDropdown();
    });

    // Pre-production items dropdown functions
    function isPreProductionDropdownOpen() {
        return materialPreProductionDropdown && materialPreProductionDropdown.style.display !== 'none';
    }

    function openPreProductionDropdown() {
        if (materialPreProductionDropdown) {
            materialPreProductionDropdown.style.display = 'block';
        }
    }

    function closePreProductionDropdown() {
        if (materialPreProductionDropdown) {
            materialPreProductionDropdown.style.display = 'none';
        }
        preProductionDropdownActiveIndex = -1;
    }

    function renderPreProductionDropdown(query = '') {
        if (!materialPreProductionDropdown) return;
        const q = query.trim().toLowerCase();
        const filtered = preProductionItemsCache
            .filter(item => (item && item.name ? String(item.name).toLowerCase().includes(q) : false))
            .slice(0, 40);

        preProductionDropdownItems = filtered;
        preProductionDropdownActiveIndex = filtered.length ? 0 : -1;

        if (filtered.length === 0) {
            materialPreProductionDropdown.innerHTML = '<div class="ds-autocomplete__option">نتیجه‌ای یافت نشد</div>';
            return;
        }

        materialPreProductionDropdown.innerHTML = filtered.map(item => {
            return `<div class="ds-autocomplete__option" data-id="${item.id}" role="option">${item.name || ''}</div>`;
        }).join('');
    }

    function updatePreProductionDropdownActive() {
        if (!materialPreProductionDropdown) return;
        const options = materialPreProductionDropdown.querySelectorAll('.ds-autocomplete__option');
        options.forEach((opt, idx) => {
            if (idx === preProductionDropdownActiveIndex) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });
    }

    function selectPreProductionItemById(id) {
        const match = preProductionItemsCache.find(item => String(item.id) === String(id));
        if (!match) return;
        if (materialPreProductionInput) materialPreProductionInput.value = match.name || '';
        if (materialPreProductionIdInput) materialPreProductionIdInput.value = match.id;
        if (materialNameInput) materialNameInput.value = match.name || '';
        if (materialUnitBadge) materialUnitBadge.textContent = match.unit_display || match.unit || '-';
        // Clear raw material selection when pre-production item is selected
        if (materialRawInput) materialRawInput.value = '';
        if (materialRawIdInput) materialRawIdInput.value = '';
        closePreProductionDropdown();
    }

    function syncPreProductionSelection() {
        if (!materialPreProductionInput) return;
        const value = materialPreProductionInput.value.trim().toLowerCase();
        let match = preProductionItemsCache.find(item => (item.name || '').toLowerCase() === value);

        if (!match && value.length > 0) {
            const partialMatches = preProductionItemsCache.filter(item => (item.name || '').toLowerCase().includes(value));
            if (partialMatches.length === 1) {
                match = partialMatches[0];
                if (materialPreProductionInput) {
                    materialPreProductionInput.value = partialMatches[0].name || '';
                }
            }
        }

        if (match) {
            if (materialPreProductionIdInput) {
                materialPreProductionIdInput.value = match.id;
            }
            if (materialNameInput) {
                materialNameInput.value = match.name;
            }
            if (materialUnitBadge) {
                materialUnitBadge.textContent = match.unit_display || match.unit || '-';
            }
            // Clear raw material selection
            if (materialRawInput) materialRawInput.value = '';
            if (materialRawIdInput) materialRawIdInput.value = '';
        } else {
            if (materialPreProductionIdInput) {
                materialPreProductionIdInput.value = '';
            }
            if (materialNameInput && !materialRawIdInput?.value) {
                materialNameInput.value = '';
            }
            if (materialUnitBadge && !materialRawIdInput?.value) {
                materialUnitBadge.textContent = '-';
            }
        }
    }

    if (materialPreProductionInput) {
        materialPreProductionInput.addEventListener('focus', function () {
            renderPreProductionDropdown(materialPreProductionInput.value);
            openPreProductionDropdown();
        });
        materialPreProductionInput.addEventListener('input', function () {
            renderPreProductionDropdown(materialPreProductionInput.value);
            openPreProductionDropdown();
            syncPreProductionSelection();
            // Clear raw material selection when typing in pre-production input
            if (materialRawInput) materialRawInput.value = '';
            if (materialRawIdInput) materialRawIdInput.value = '';
        });
        materialPreProductionInput.addEventListener('change', syncPreProductionSelection);
        materialPreProductionInput.addEventListener('keydown', function (e) {
            if (!preProductionDropdownItems || preProductionDropdownItems.length === 0) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!isPreProductionDropdownOpen()) openPreProductionDropdown();
                preProductionDropdownActiveIndex = Math.min(preProductionDropdownActiveIndex + 1, preProductionDropdownItems.length - 1);
                updatePreProductionDropdownActive();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!isPreProductionDropdownOpen()) openPreProductionDropdown();
                preProductionDropdownActiveIndex = Math.max(preProductionDropdownActiveIndex - 1, 0);
                updatePreProductionDropdownActive();
            } else if (e.key === 'Enter') {
                if (!isPreProductionDropdownOpen()) return;
                e.preventDefault();
                const current = preProductionDropdownItems[preProductionDropdownActiveIndex];
                if (current && current.id != null) {
                    selectPreProductionItemById(current.id);
                }
            } else if (e.key === 'Escape') {
                closePreProductionDropdown();
            }
        });
    }

    if (materialPreProductionDropdown) {
        materialPreProductionDropdown.addEventListener('click', function (e) {
            const option = e.target.closest('.ds-autocomplete__option');
            if (!option) return;
            const id = option.getAttribute('data-id');
            if (id) {
                selectPreProductionItemById(id);
            }
        });
    }

    document.addEventListener('click', function (e) {
        if (!materialPreProductionAutocomplete || !materialPreProductionDropdown) return;
        if (materialPreProductionAutocomplete.contains(e.target)) return;
        closePreProductionDropdown();
    });

    // Clear pre-production selection when raw material is selected
    if (materialRawInput) {
        const originalSync = syncRawMaterialSelection;
        syncRawMaterialSelection = function() {
            originalSync();
            if (materialPreProductionInput) materialPreProductionInput.value = '';
            if (materialPreProductionIdInput) materialPreProductionIdInput.value = '';
        };
    }

    function renderMaterialsList(materials) {
        if (!materialsListEl) return;
        if (!materials || materials.length === 0) {
            materialsListEl.classList.add('empty');
            materialsListEl.innerHTML = 'متریالی ثبت نشده است.';
            // مخفی کردن جمع کل
            const materialsTotal = document.getElementById('materials-total');
            if (materialsTotal) {
                materialsTotal.style.display = 'none';
            }
            if (materialsSummaryCount) {
                materialsSummaryCount.textContent = '۰';
            }
            return;
        }

        function escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        materialsListEl.classList.remove('empty');
        materialsListEl.innerHTML = '';
        let totalCost = 0;
        
        materials.forEach(material => {
            const row = document.createElement('div');
            row.className = 'materials-item';

            const displayName = escapeHtml(material.name || material.raw_material_name || '---');
            const unitLabel = escapeHtml(material.unit_display || material.unit || '');
            const quantityLabel = material.quantity ? `${material.quantity} ${unitLabel}`.trim() : unitLabel;

            const unitPrice = material.latest_unit_price ? Number(material.latest_unit_price) : null;
            const estimatedCost = material.estimated_cost ? Number(material.estimated_cost) : null;

            if (estimatedCost) {
                totalCost += estimatedCost;
            }

            const metaPills = [];
            if (unitPrice) {
                metaPills.push(`<span class="materials-pill">قیمت واحد: ${unitPrice.toLocaleString('fa-IR')}</span>`);
            }
            if (material.raw_material_unit_display && !String(material.raw_material_unit_display).includes(unitLabel)) {
                metaPills.push(`<span class="materials-pill">${escapeHtml(material.raw_material_unit_display)}</span>`);
            }

            row.innerHTML = `
                <div class="materials-item__main">
                    <div class="materials-item__title">
                        <strong class="materials-item__name">${displayName}</strong>
                        <span class="materials-item__qty">${escapeHtml(quantityLabel || '-')}</span>
                    </div>
                    ${metaPills.length ? `<div class="materials-item__meta">${metaPills.join('')}</div>` : ''}
                </div>
                <div class="materials-item__side">
                    <div class="materials-item__cost">
                        <span class="materials-item__cost-label">هزینه</span>
                        <strong class="materials-item__cost-value">${estimatedCost ? estimatedCost.toLocaleString('fa-IR') : '-'}</strong>
                    </div>
                    <button type="button" class="materials-item__delete material-delete-btn" data-material-id="${escapeHtml(material.id)}">حذف</button>
                </div>
            `;

            materialsListEl.appendChild(row);
        });
        if (materialsSummaryCount) {
            materialsSummaryCount.textContent = materials.length.toLocaleString('fa-IR');
        }
        
        // نمایش جمع کل هزینه
        const materialsTotal = document.getElementById('materials-total');
        const materialsTotalValue = document.getElementById('materials-total-value');
        if (materialsTotal && materialsTotalValue) {
            materialsTotalValue.textContent = `${totalCost.toLocaleString('fa-IR')}`;
            materialsTotal.style.display = 'block';
        }
    }
});

// حذف آیتم منو بدون مدال (استفاده از Event Delegation در سطح document)
// NOTE: This is the ONLY delete-btn handler kept
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('delete-btn')) {
        const itemId = e.target.getAttribute('data-id');
        if (!itemId) return;
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
                if (data.success || Object.keys(data).length === 0) {
                    const item = e.target.closest('.menu-item');
                    if (item) item.remove();
                } else {
                    alert('خطا در حذف آیتم' + (data.message ? ': ' + data.message : ''));
                }
            })
            .catch(err => {
                console.error('حذف آیتم با خطا مواجه شد:', err);
                alert('خطا در ارتباط با سرور یا پردازش پاسخ: ' + err.message);
            });
    }
});

// مدیریت دسته‌بندی‌ها
document.addEventListener('DOMContentLoaded', function() {
    const manageCategoriesBtn = document.getElementById('manage-categories-btn');
    const categoriesModal = document.getElementById('categoriesModal');
    const categoryFormModal = document.getElementById('categoryFormModal');
    const addCategoryBtn = document.getElementById('add-category-btn');
    const categoryForm = document.getElementById('category-form');
    const categoriesList = document.getElementById('categories-list');
    const categoryModalTitle = document.getElementById('category-modal-title');
    
    // باز کردن مودال مدیریت دسته‌بندی‌ها
    if (manageCategoriesBtn) {
        manageCategoriesBtn.addEventListener('click', function() {
            loadCategories();
            categoriesModal.style.display = 'block';
        });
    }
    
    // بستن مودال‌ها
    const closeModals = document.querySelectorAll('#categoriesModal .close-modal, #categoryFormModal .close-modal');
    closeModals.forEach(btn => {
        btn.addEventListener('click', function() {
            categoriesModal.style.display = 'none';
            categoryFormModal.style.display = 'none';
        });
    });
    
    // باز کردن فرم افزودن دسته‌بندی
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', function() {
            categoryForm.reset();
            document.getElementById('category-id').value = '';
            categoryModalTitle.textContent = 'افزودن دسته‌بندی';
            categoryFormModal.style.display = 'block';
        });
    }
    
    // بارگذاری لیست دسته‌بندی‌ها
    function loadCategories() {
        fetch('/menu/category/list')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    renderCategories(data.categories);
                }
            })
            .catch(err => {
                console.error('خطا در بارگذاری دسته‌بندی‌ها:', err);
            });
    }
    
    // نمایش لیست دسته‌بندی‌ها
    function renderCategories(categories) {
        if (!categoriesList) return;
        
        if (categories.length === 0) {
            categoriesList.innerHTML = '<p class="ds-subtitle">هیچ دسته‌بندی‌ای وجود ندارد.</p>';
            return;
        }
        
        let html = '<div style="display: flex; flex-direction: column; gap: 0.75rem;">';
        categories.forEach(cat => {
            html += `
                <div class="ds-card" style="padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0 0 0.25rem 0;">${cat.name}</h4>
                        ${cat.description ? `<p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">${cat.description}</p>` : ''}
                        <span class="ds-pill" style="margin-top: 0.5rem;">${cat.items_count} آیتم</span>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="ds-button ghost edit-category-btn" data-id="${cat.id}" data-name="${cat.name}" data-description="${cat.description || ''}" data-order="${cat.order}">ویرایش</button>
                        <button class="ds-button danger delete-category-btn" data-id="${cat.id}" data-name="${cat.name}">حذف</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        categoriesList.innerHTML = html;
        
        // اضافه کردن event listener برای دکمه‌های ویرایش
        document.querySelectorAll('.edit-category-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const name = this.getAttribute('data-name');
                const description = this.getAttribute('data-description');
                const order = this.getAttribute('data-order');
                
                document.getElementById('category-id').value = id;
                document.getElementById('category-name').value = name;
                document.getElementById('category-description').value = description;
                document.getElementById('category-order').value = order;
                categoryModalTitle.textContent = 'ویرایش دسته‌بندی';
                categoryFormModal.style.display = 'block';
            });
        });
        
        // اضافه کردن event listener برای دکمه‌های حذف
        document.querySelectorAll('.delete-category-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const name = this.getAttribute('data-name');
                
                if (confirm(`آیا از حذف دسته‌بندی "${name}" مطمئن هستید؟`)) {
                    fetch(`/menu/category/${id}/delete`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(async response => {
                        const contentType = response.headers.get('content-type');
                        if (contentType && contentType.includes('application/json')) {
                            return await response.json();
                        } else {
                            // اگر پاسخ JSON نبود، متن خطا را برمی‌گردانیم
                            const text = await response.text();
                            throw new Error(`خطای سرور (${response.status}): ${text.substring(0, 100)}`);
                        }
                    })
                    .then(data => {
                        if (data.status === 'success') {
                            alert(data.message);
                            loadCategories();
                            location.reload(); // برای به‌روزرسانی صفحه
                        } else {
                            alert('خطا: ' + (data.message || 'خطای نامشخص'));
                        }
                    })
                    .catch(err => {
                        console.error('خطا:', err);
                        alert('خطا در حذف دسته‌بندی: ' + err.message);
                    });
                }
            });
        });
    }
    
    // ذخیره دسته‌بندی
    if (categoryForm) {
        categoryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const id = document.getElementById('category-id').value;
            const name = document.getElementById('category-name').value.trim();
            const description = document.getElementById('category-description').value.trim();
            const order = parseInt(document.getElementById('category-order').value) || 0;
            
            if (!name) {
                alert('نام دسته‌بندی الزامی است');
                return;
            }
            
            const url = id ? `/menu/category/${id}/edit` : '/menu/category/add';
            const method = 'POST';
            
            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, description, order })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    categoryFormModal.style.display = 'none';
                    loadCategories();
                    location.reload(); // برای به‌روزرسانی صفحه
                } else {
                    alert('خطا: ' + (data.message || 'خطای نامشخص'));
                }
            })
            .catch(err => {
                console.error('خطا:', err);
                alert('خطا در ذخیره دسته‌بندی');
            });
        });
    }
    
    // فیلتر کردن بر اساس دسته‌بندی
    const categoryLinks = document.querySelectorAll('.menu-category-link');
    categoryLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // حذف active از همه لینک‌ها
            categoryLinks.forEach(l => l.classList.remove('active'));
            // اضافه کردن active به لینک کلیک شده
            this.classList.add('active');
            
            const categoryId = this.getAttribute('data-category-id');
            
            // مخفی کردن همه بلوک‌های دسته‌بندی
            document.querySelectorAll('.category-block').forEach(block => {
                block.style.display = 'none';
            });
            
            // نمایش بلوک مربوطه
            if (categoryId === 'all') {
                document.getElementById('all-items').style.display = 'block';
            } else {
                const categoryBlock = document.getElementById(`category-${categoryId}`);
                if (categoryBlock) {
                    categoryBlock.style.display = 'block';
                }
            }
        });
    });
    
    // جستجو در آیتم‌های منو
    const menuSearchInput = document.getElementById('menu-search');
    if (menuSearchInput) {
        menuSearchInput.addEventListener('input', function(e) {
            const searchQuery = e.target.value.trim().toLowerCase();
            filterMenuItems(searchQuery);
        });
        
        menuSearchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Escape') {
                e.target.value = '';
                filterMenuItems('');
            }
        });
    }
    
    function filterMenuItems(searchQuery) {
        // دریافت همه کارت‌های آیتم
        const allMenuItems = document.querySelectorAll('.menu-item');
        let visibleCount = 0;
        
        allMenuItems.forEach(item => {
            const nameInput = item.querySelector('.inline-name');
            const itemName = nameInput ? nameInput.value.toLowerCase() : '';
            
            if (!searchQuery || itemName.includes(searchQuery)) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });
        
        // به‌روزرسانی تعداد آیتم‌های قابل مشاهده در هر گروه
        const categoryGroups = document.querySelectorAll('.category-group');
        categoryGroups.forEach(group => {
            const itemsInGroup = group.querySelectorAll('.menu-item');
            const visibleInGroup = Array.from(itemsInGroup).filter(item => item.style.display !== 'none').length;
            
            // به‌روزرسانی تعداد در هدر گروه
            const pillElement = group.querySelector('.ds-pill');
            if (pillElement) {
                pillElement.textContent = `${visibleInGroup} محصول`;
            }
            
            // اگر همه آیتم‌های گروه مخفی شدند، کل گروه را مخفی کن
            if (visibleInGroup === 0) {
                group.style.display = 'none';
            } else {
                group.style.display = '';
            }
        });
        
        // به‌روزرسانی تعداد کل در هدر "همه آیتم‌ها"
        const allItemsHeader = document.querySelector('#all-items .ds-card-header .ds-pill');
        if (allItemsHeader) {
            allItemsHeader.textContent = `${visibleCount} آیتم`;
        }
    }
});
