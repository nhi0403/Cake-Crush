/**
 * Cake Crush HR - Searchable Select Component
 * Chuyển đổi các thẻ <select> thành thanh tìm kiếm trực quan có autocomplete/dropdown lọc dữ liệu.
 */
function initSearchableSelect(selectEl, customPlaceholder) {
    if (!selectEl) return null;
    if (selectEl.dataset.searchableInit === "true") {
        if (selectEl.refreshSearchable) selectEl.refreshSearchable();
        return;
    }
    selectEl.dataset.searchableInit = "true";

    // Ẩn select gốc nhưng giữ lại trong DOM để form submit & serialize bình thường
    selectEl.style.display = "none";

    const wrapper = document.createElement("div");
    wrapper.className = "dt-search-wrapper";

    const inputWrap = document.createElement("div");
    inputWrap.className = "dt-search-input-wrap";

    const searchIcon = document.createElement("i");
    searchIcon.className = "fa-solid fa-magnifying-glass dt-search-icon";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "dt-search-input";
    input.autocomplete = "off";

    // Placeholder mặc định
    const firstOpt = selectEl.querySelector("option");
    const placeholderText = customPlaceholder || selectEl.getAttribute("data-placeholder") || (firstOpt && firstOpt.value === "" ? firstOpt.textContent : "Tìm kiếm...");
    input.placeholder = placeholderText;

    // Nút xóa (clear)
    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "dt-search-clear";
    clearBtn.innerHTML = "&times;";
    clearBtn.title = "Xóa lựa chọn";
    clearBtn.style.display = "none";

    // Mũi tên chỉ xuống
    const arrowIcon = document.createElement("i");
    arrowIcon.className = "fa-solid fa-chevron-down dt-search-arrow";

    inputWrap.appendChild(searchIcon);
    inputWrap.appendChild(input);
    inputWrap.appendChild(clearBtn);
    inputWrap.appendChild(arrowIcon);

    // Dropdown danh sách kết quả
    const dropdown = document.createElement("div");
    dropdown.className = "dt-search-dropdown";

    wrapper.appendChild(inputWrap);
    wrapper.appendChild(dropdown);
    selectEl.parentNode.insertBefore(wrapper, selectEl.nextSibling);

    function buildOptions() {
        dropdown.innerHTML = "";
        const options = Array.from(selectEl.options);
        let hasValid = false;

        options.forEach(opt => {
            if (opt.value === "") return; // Bỏ qua tùy chọn rỗng
            hasValid = true;
            const item = document.createElement("div");
            item.className = "dt-search-item" + (opt.selected ? " is-selected" : "");
            item.dataset.value = opt.value;
            item.textContent = opt.textContent;

            item.addEventListener("mousedown", (e) => {
                e.preventDefault();
                selectOption(opt.value, opt.textContent);
            });
            dropdown.appendChild(item);
        });

        const empty = document.createElement("div");
        empty.className = "dt-search-empty";
        empty.textContent = "Không tìm thấy kết quả phù hợp";
        empty.style.display = hasValid ? "none" : "block";
        dropdown.appendChild(empty);

        syncSelectedText();
    }

    function syncSelectedText() {
        const selectedOpt = selectEl.options[selectEl.selectedIndex];
        if (selectedOpt && selectedOpt.value !== "") {
            input.value = selectedOpt.textContent.trim();
            clearBtn.style.display = "block";
            wrapper.classList.add("has-value");
        } else {
            input.value = "";
            clearBtn.style.display = "none";
            wrapper.classList.remove("has-value");
        }

        if (selectEl.disabled) {
            input.disabled = true;
            wrapper.classList.add("is-disabled");
        } else {
            input.disabled = false;
            wrapper.classList.remove("is-disabled");
        }
    }

    function filterOptions(query) {
        const q = (query || "").toLowerCase().trim();
        const items = dropdown.querySelectorAll(".dt-search-item");
        let matchCount = 0;

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (!q || text.includes(q)) {
                item.style.display = "flex";
                matchCount++;
            } else {
                item.style.display = "none";
            }
        });

        const empty = dropdown.querySelector(".dt-search-empty");
        if (empty) {
            empty.style.display = matchCount === 0 ? "block" : "none";
        }
    }

    function openDropdown() {
        if (selectEl.disabled) return;
        buildOptions();
        filterOptions(input.value);
        dropdown.classList.add("show");
        wrapper.classList.add("is-open");
    }

    function closeDropdown() {
        dropdown.classList.remove("show");
        wrapper.classList.remove("is-open");
        syncSelectedText();
    }

    function selectOption(val, text) {
        selectEl.value = val;
        input.value = text.trim();
        clearBtn.style.display = "block";
        wrapper.classList.add("has-value");
        dropdown.classList.remove("show");
        wrapper.classList.remove("is-open");

        // Bắn sự kiện change để các script xử lý form hoạt động
        const event = new Event("change", { bubbles: true });
        selectEl.dispatchEvent(event);
    }

    function clearSelection() {
        selectEl.value = "";
        input.value = "";
        clearBtn.style.display = "none";
        wrapper.classList.remove("has-value");
        filterOptions("");
        const event = new Event("change", { bubbles: true });
        selectEl.dispatchEvent(event);
        input.focus();
    }

    input.addEventListener("focus", openDropdown);
    input.addEventListener("input", () => {
        openDropdown();
        clearBtn.style.display = input.value ? "block" : "none";
        filterOptions(input.value);
    });

    arrowIcon.addEventListener("click", () => {
        if (dropdown.classList.contains("show")) {
            closeDropdown();
        } else {
            input.focus();
            openDropdown();
            filterOptions("");
        }
    });

    clearBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        clearSelection();
    });

    document.addEventListener("click", (e) => {
        if (!wrapper.contains(e.target)) {
            closeDropdown();
        }
    });

    selectEl.refreshSearchable = function () {
        buildOptions();
    };

    buildOptions();
    return wrapper;
}
