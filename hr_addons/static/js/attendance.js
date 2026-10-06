document.addEventListener("DOMContentLoaded", function () {
    // --- Global State ---
    let allAttendanceLogs = [];
    let currentFilteredLogs = [];
    let currentPage = 1;
    const rowsPerPage = 40;

    let weeklyChart = null;
    let statusDoughnutChart = null;

    // --- DOM Elements ---
    const searchInput = document.getElementById('searchInput');
    const departmentFilter = document.getElementById('departmentFilter');
    const statusFilter = document.getElementById('statusFilter');
    const companyFilter = document.getElementById('companyFilter');
    const districtFilter = document.getElementById('districtFilter');
    const startDateFilter = document.getElementById('startDateFilter');
    const endDateFilter = document.getElementById('endDateFilter');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');

    // --- Event Listeners Setup ---
    searchInput?.addEventListener('input', applyFilters);
    departmentFilter?.addEventListener('change', applyFilters);
    statusFilter?.addEventListener('change', applyFilters);
    companyFilter?.addEventListener('change', applyFilters);
    districtFilter?.addEventListener('change', applyFilters);
    startDateFilter?.addEventListener('change', applyFilters);
    endDateFilter?.addEventListener('change', applyFilters);

    clearFiltersBtn?.addEventListener('click', resetAllFilters);
    exportCsvBtn?.addEventListener('click', exportFilteredToCSV);

    const loadingOverlay = document.getElementById('loadingOverlay');

    function showLoader() {
        if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    }

    function hideLoader() {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
    // --- 1. Fetch Data from Odoo Controller ---
    async function fetchOdooAttendance() {
        showLoader();
        try {
            const response = await fetch('/api/attendance/dashboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ params: {} })
            });

            const result = await response.json();
            if (result.result) {
                const data = result.result;
                
                // Update KPI & Charts
                if (data.summary) updateKPICards(data.summary);
                if (data.summary && data.weekly_trend) updateCharts(data.summary, data.weekly_trend);

                // Populate global data logs
                allAttendanceLogs = data.logs || [];

                // Populate filter dropdowns dynamically
                populateDepartmentDropdown(allAttendanceLogs);
                populateDistrictDropdown(allAttendanceLogs);
                populateCompanyDropdown(allAttendanceLogs);

                // Initial render via filter pipeline
                applyFilters();
            }
        } catch (error) {
            console.error("Failed to load Odoo attendance records:", error);
        }
        finally {
            hideLoader(); // Turn off spinner once all data & DOM updates are finished
        }
    }

    // --- 2. Dynamic Metric Updates ---
    function updateKPICards(summary) {
        const kpiTotal = document.getElementById('kpiTotal');
        const kpiPresent = document.getElementById('kpiPresent');
        const kpiLate = document.getElementById('kpiLate');
        const kpiAbsent = document.getElementById('kpiAbsent');

        if (kpiTotal) kpiTotal.textContent = summary.total_personnel || 0;
        if (kpiPresent) kpiPresent.innerHTML = `${summary.present || 0} <small class="fs-6 text-muted">(${summary.present_rate || 0}%)</small>`;
        if (kpiLate) kpiLate.textContent = summary.late || 0;
        if (kpiAbsent) kpiAbsent.textContent = summary.absent || 0;
    }

    // --- 3. Dynamic Chart Rendering ---
    function updateCharts(summary, weeklyTrend) {
        if (typeof Chart === 'undefined') return;

        // 1. Weekly Line Chart
        const weeklyCanvas = document.getElementById('weeklyChart');
        if (weeklyCanvas) {
            const existingWeeklyChart = Chart.getChart(weeklyCanvas);
            if (existingWeeklyChart) existingWeeklyChart.destroy();

            weeklyChart = new Chart(weeklyCanvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: weeklyTrend.labels || [],
                    datasets: [{
                        label: 'Attendance Rate (%)',
                        data: weeklyTrend.data || [],
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.08)',
                        tension: 0.35,
                        fill: true,
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { min: 0, max: 100 } }
                }
            });
        }

        // 2. Status Doughnut Chart
        const statusCanvas = document.getElementById('statusDoughnutChart');
        if (statusCanvas) {
            const existingStatusChart = Chart.getChart(statusCanvas);
            if (existingStatusChart) existingStatusChart.destroy();

            statusDoughnutChart = new Chart(statusCanvas.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Punctual', 'Late', 'Absent / Leave'],
                    datasets: [{
                        data: [
                            (summary.present || 0) - (summary.late || 0),
                            summary.late || 0,
                            summary.absent || 0
                        ],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    }

    // --- 4. Dropdown Dynamic Population ---
    function populateDepartmentDropdown(logs) {
        if (!departmentFilter) return;
        const departments = [...new Set(logs.map(item => item.department).filter(Boolean))].sort();

        departmentFilter.innerHTML = '<option value="">All Departments</option>';
        departments.forEach(dept => {
            const opt = document.createElement('option');
            opt.value = dept;
            opt.textContent = dept;
            departmentFilter.appendChild(opt);
        });
    }

    function populateDistrictDropdown(logs) {
        if (!districtFilter) return;
        const districts = [...new Set(logs.map(item => item.district).filter(Boolean))].sort();

        districtFilter.innerHTML = '<option value="">All District</option>';
        districts.forEach(dist => {
            const opt = document.createElement('option');
            opt.value = dist;
            opt.textContent = dist;
            districtFilter.appendChild(opt);
        });
    }

    function populateCompanyDropdown(logs) {
        if (!companyFilter) return;
        const companies = [...new Set(logs.map(item => item.company).filter(Boolean))].sort();

        companyFilter.innerHTML = '<option value="">All company</option>';
        companies.forEach(comp => {
            const opt = document.createElement('option');
            opt.value = comp;
            opt.textContent = comp;
            companyFilter.appendChild(opt);
        });
    }

    // --- Multi-Filter Logic ---
function applyFilters() {
    const searchTerm = (searchInput?.value || '').toLowerCase().trim();
    const selectedDept = (departmentFilter?.value || '').toLowerCase();
    const selectedStatus = (statusFilter?.value || '').toLowerCase();
    const selectedCompany = (companyFilter?.value || '').toLowerCase();
    const selectedDistrict = (districtFilter?.value || '').toLowerCase();

    // Safe Date Range Normalization
    let startTime = null;
    let endTime = null;

    if (startDateFilter?.value) {
        // Force start date to midnight (00:00:00.000) local time
        const [sYear, sMonth, sDay] = startDateFilter.value.split('-').map(Number);
        startTime = new Date(sYear, sMonth - 1, sDay, 0, 0, 0, 0).getTime();
    }

    if (endDateFilter?.value) {
        // Force end date to end-of-day (23:59:59.999) local time
        const [eYear, eMonth, eDay] = endDateFilter.value.split('-').map(Number);
        endTime = new Date(eYear, eMonth - 1, eDay, 23, 59, 59, 999).getTime();
    }

    currentFilteredLogs = allAttendanceLogs.filter(log => {
        if (!log) return false;

        const empName = (log.employee_name || '').toLowerCase();
        const empCode = (log.employee_code || '').toLowerCase();
        const logDept = (log.department || '').toLowerCase();
        const logStatus = (log.status || '').toLowerCase();
        const logCompany = (log.company || '').toLowerCase();
        const logDistrict = (log.district || '').toLowerCase();

        // Text & Dropdown Matches
        const matchesSearch = empName.includes(searchTerm) || empCode.includes(searchTerm);
        const matchesDept = !selectedDept || logDept === selectedDept;
        const matchesStatus = !selectedStatus || logStatus === selectedStatus;
        const matchesCompany = !selectedCompany || logCompany === selectedCompany;
        const matchesDistrict = !selectedDistrict || logDistrict === selectedDistrict;

        // Date Range Match
        let matchesDateRange = true;
        if (startTime !== null || endTime !== null) {
            // Extract log timestamp (check_in or date)
            const rawDateStr = log.check_in || log.date;
            
            if (rawDateStr) {
                // Replace space with 'T' so Safari & Firefox reliably parse Odoo ISO datetimes (YYYY-MM-DD HH:MM:SS)
                const safeDateStr = String(rawDateStr).trim().replace(' ', 'T');
                const logTime = new Date(safeDateStr).getTime();

                if (!isNaN(logTime)) {
                    if (startTime !== null && logTime < startTime) matchesDateRange = false;
                    if (endTime !== null && logTime > endTime) matchesDateRange = false;
                } else {
                    matchesDateRange = false; // Fallback if date is invalid
                }
            } else {
                matchesDateRange = false; // Exclude logs missing date values when date filter is set
            }
        }

        return matchesSearch && matchesDept && matchesStatus && matchesCompany && matchesDistrict && matchesDateRange;
    });

    currentPage = 1;
    renderPaginatedTable();
}

    // --- 6. Reset Filters ---
    function resetAllFilters() {
        if (searchInput) searchInput.value = '';
        if (departmentFilter) departmentFilter.value = '';
        if (statusFilter) statusFilter.value = '';
        if (companyFilter) companyFilter.value = '';
        if (districtFilter) districtFilter.value = '';
        if (startDateFilter) startDateFilter.value = '';
        if (endDateFilter) endDateFilter.value = '';

        applyFilters();
    }

    // --- 7. Table & Pagination Rendering ---
    function renderPaginatedTable() {
        const totalRecords = currentFilteredLogs.length;
        const totalPages = Math.ceil(totalRecords / rowsPerPage) || 1;

        if (currentPage < 1) currentPage = 1;
        if (currentPage > totalPages) currentPage = totalPages;

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = Math.min(startIndex + rowsPerPage, totalRecords);
        const pageData = currentFilteredLogs.slice(startIndex, endIndex);

        renderTable(pageData);

        const infoContainer = document.getElementById('paginationInfo');
        if (infoContainer) {
            infoContainer.textContent = totalRecords > 0 
                ? `Showing ${startIndex + 1} to ${endIndex} of ${totalRecords} records`
                : `Showing 0 to 0 of 0 records`;
        }

        renderPaginationControls(totalPages);
    }

    function renderTable(logs) {
        const tbody = document.querySelector('#attendanceTable tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No attendance logs found.</td></tr>`;
            return;
        }

        logs.forEach(log => {
            let badgeClass = 'bg-success';
            if (log.status === 'Late') badgeClass = 'bg-warning text-dark';
            if (log.status === 'Absent') badgeClass = 'bg-danger';
            if (log.status === 'On Leave') badgeClass = 'bg-info text-dark';

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <img src="${log.avatar_url || ''}" class="avatar rounded-circle" style="width:32px;height:32px;object-fit:cover;" alt="Avatar" onerror="this.src='https://i.pravatar.cc/100?u=${log.employee_code || 'default'}'">
                        <div>
                            <div class="fw-semibold">${escapeHtml(log.employee_name)}</div>
                            <small class="text-muted">${escapeHtml(log.employee_code)}</small>
                        </div>
                    </div>
                </td>
                <td>${escapeHtml(log.department)}</td>
                <td>${escapeHtml(log.company)}</td>
                <td>${escapeHtml(log.district)}</td>
                <td>${escapeHtml(log.check_in)}</td>
                <td>${escapeHtml(log.check_out)}</td>
                <td><span class="fw-medium">${log.worked_hours || 0} hrs</span></td>
                <td><span class="badge ${badgeClass} px-2 py-1">${escapeHtml(log.status)}</span></td>
            `;
            tbody.appendChild(row);
        });
    }

    function renderPaginationControls(totalPages) {
        const paginationContainer = document.getElementById('paginationControls');
        if (!paginationContainer) return;

        paginationContainer.innerHTML = '';
        if (totalPages <= 1) return;

        // Previous Button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" aria-label="Previous">&laquo; Prev</a>`;
        prevLi.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage > 1) {
                currentPage--;
                renderPaginatedTable();
            }
        });
        paginationContainer.appendChild(prevLi);

        // Page Numbers
        for (let page = 1; page <= totalPages; page++) {
            const isFirstPage = page === 1;
            const isLastPage = page === totalPages;
            const isNearCurrent = page >= currentPage - 1 && page <= currentPage + 1;

            if (isFirstPage || isLastPage || isNearCurrent) {
                const pageLi = document.createElement('li');
                pageLi.className = `page-item ${page === currentPage ? 'active' : ''}`;
                pageLi.innerHTML = `<a class="page-link" href="#">${page}</a>`;
                pageLi.addEventListener('click', (e) => {
                    e.preventDefault();
                    currentPage = page;
                    renderPaginatedTable();
                });
                paginationContainer.appendChild(pageLi);
            } else if (
                (page === currentPage - 2 && currentPage > 3) || 
                (page === currentPage + 2 && currentPage < totalPages - 2)
            ) {
                const dotsLi = document.createElement('li');
                dotsLi.className = 'page-item disabled';
                dotsLi.innerHTML = `<span class="page-link">...</span>`;
                paginationContainer.appendChild(dotsLi);
            }
        }

        // Next Button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" aria-label="Next">Next &raquo;</a>`;
        nextLi.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage < totalPages) {
                currentPage++;
                renderPaginatedTable();
            }
        });
        paginationContainer.appendChild(nextLi);
    }

    // --- 8. CSV Export ---
    function exportFilteredToCSV() {
        if (!currentFilteredLogs || currentFilteredLogs.length === 0) {
            alert("No records available to export.");
            return;
        }

        const headers = ["Employee ID", "Employee Name", "Department", "Company", "District", "Check In", "Check Out", "Worked Hours", "Status"];
        const csvRows = [headers.join(",")];

        currentFilteredLogs.forEach(log => {
            const row = [
                `"${escapeCsvValue(log.employee_code)}"`,
                `"${escapeCsvValue(log.employee_name)}"`,
                `"${escapeCsvValue(log.department)}"`,
                `"${escapeCsvValue(log.company)}"`,
                `"${escapeCsvValue(log.district)}"`,
                `"${escapeCsvValue(log.check_in)}"`,
                `"${escapeCsvValue(log.check_out)}"`,
                `"${log.worked_hours || 0}"`,
                `"${escapeCsvValue(log.status)}"`
            ];
            csvRows.push(row.join(","));
        });

        const csvContent = "\uFEFF" + csvRows.join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const todayStr = new Date().toISOString().split('T')[0];
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `attendance_report_${todayStr}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // --- Utilities ---
    function escapeCsvValue(val) {
        if (!val) return '';
        return String(val).replace(/"/g, '""');
    }

    function escapeHtml(str) {
        return String(str || '').replace(/[&<>"']/g, function(m) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
        });
    }

    // --- Entry Point ---
    fetchOdooAttendance();
});