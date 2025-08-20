odoo.define('appraisals.data', function (require) {
  'use strict';

  const _data = [
    { id: '1', employee: 'Jane Doe', staff_id: 'EEDC-00123', department: 'Engineering', email: 'jane.doe@example.com', role: 'Senior Developer', year: '2025', supervisor: 'Samuel Ajayi', manager_review: 15, employee_rating: 5, reviewer_rating: 10, total: 30 },
    { id: '2', employee: 'John Smith', staff_id: 'EEDC-00124', department: 'IT Operations', email: 'john.smith@example.com', role: 'DevOps Engineer', year: '2025', supervisor: 'Ruth Mika', manager_review: 12, employee_rating: 6, reviewer_rating: 9, total: 27 },
    { id: '3', employee: 'Ada Eze', staff_id: 'EEDC-00125', department: 'Finance', email: 'ada.eze@example.com', role: 'Analyst', year: '2024', supervisor: 'Kunle Ojo', manager_review: 14, employee_rating: 7, reviewer_rating: 8, total: 29 },
    { id: '4', employee: 'Chinedu Okeke', staff_id: 'EEDC-00126', department: 'HR', email: 'chinedu.okeke@example.com', role: 'HRBP', year: '2025', supervisor: 'Ngozi Obi', manager_review: 13, employee_rating: 8, reviewer_rating: 9, total: 30 },
    { id: '5', employee: 'Yemi Alade', staff_id: 'EEDC-00127', department: 'Customer Service', email: 'yemi.alade@example.com', role: 'Team Lead', year: '2025', supervisor: 'Tunji Bello', manager_review: 10, employee_rating: 7, reviewer_rating: 7, total: 24 },
    { id: '6', employee: 'Bola Akin', staff_id: 'EEDC-00128', department: 'Engineering', email: 'bola.akin@example.com', role: 'QA Engineer', year: '2024', supervisor: 'Samuel Ajayi', manager_review: 11, employee_rating: 6, reviewer_rating: 8, total: 25 },
    { id: '7', employee: 'Ifeanyi Nwosu', staff_id: 'EEDC-00129', department: 'Procurement', email: 'ifeanyi.nwosu@example.com', role: 'Officer', year: '2023', supervisor: 'Irene Yusuf', manager_review: 9, employee_rating: 6, reviewer_rating: 7, total: 22 },
    { id: '8', employee: 'Mary Okon', staff_id: 'EEDC-00130', department: 'Legal', email: 'mary.okon@example.com', role: 'Counsel', year: '2025', supervisor: 'Bassey Etim', manager_review: 16, employee_rating: 7, reviewer_rating: 9, total: 32 },
    { id: '9', employee: 'Sola Ade', staff_id: 'EEDC-00131', department: 'Engineering', email: 'sola.ade@example.com', role: 'Intern', year: '2025', supervisor: 'Samuel Ajayi', manager_review: 7, employee_rating: 6, reviewer_rating: 6, total: 19 },
    { id: '10', employee: 'Halima Musa', staff_id: 'EEDC-00132', department: 'Operations', email: 'halima.musa@example.com', role: 'Coordinator', year: '2024', supervisor: 'Danladi Umar', manager_review: 12, employee_rating: 8, reviewer_rating: 8, total: 28 },
  ];

  function getAll() { return _data.slice(); }
  function getById(id) { return _data.find(r => String(r.id) === String(id)); }

  return { getAll, getById };
});