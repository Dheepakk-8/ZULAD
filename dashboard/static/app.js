const el = (id) => document.getElementById(id);

async function loadFilters() {
  const data = await (await fetch('/api/filters')).json();
  [['course_id', data.courses], ['group_id', data.groups], ['learner_id', data.learners]].forEach(([id, items]) => {
    const select = el(id);
    items.slice(0, 2000).forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.name || `${item.name} (${item.email})`;
      select.appendChild(option);
    });
  });
}

function params() {
  const p = new URLSearchParams();
  ['date_from', 'date_to', 'course_id', 'group_id', 'learner_id'].forEach(id => {
    const v = el(id).value;
    if (v) p.set(id, v);
  });
  const band = el('completion_band').value;
  if (band) {
    const [min, max] = band.split('-');
    p.set('completion_min', min);
    p.set('completion_max', max);
  }
  return p;
}

function render(data) {
  const kpiContainer = el('kpis');
  kpiContainer.innerHTML = '';
  const kpis = [
    ['Courses Taken', data.kpis.courses_taken],
    ['Users Enrolled', data.kpis.users_enrolled],
    ['Users Completed', data.kpis.users_completed],
    ['Users Dropped', data.kpis.users_dropped],
    ['Completion %', data.kpis.completion_percentage],
  ];
  kpis.forEach(([label, value]) => {
    const card = document.createElement('div');
    card.className = 'kpi';
    card.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    kpiContainer.appendChild(card);
  });

  el('course_rows').innerHTML = data.courses.map(row => `
    <tr>
      <td>${row.course_name}</td>
      <td>${row.enrollments}</td>
      <td>${row.completed}</td>
      <td>${row.completion_percentage}</td>
      <td>${row.drop_rate}</td>
    </tr>
  `).join('');

  el('insights').innerHTML = data.insights.map(i => `<li>${i}</li>`).join('');
}

async function search() {
  const data = await (await fetch(`/api/dashboard?${params().toString()}`)).json();
  render(data);
}

function reset() {
  ['date_from', 'date_to', 'course_id', 'group_id', 'learner_id', 'completion_band'].forEach(id => el(id).value = '');
  search();
}

function exportData(format) {
  window.location.href = `/api/export?format=${format}&${params().toString()}`;
}

el('search').addEventListener('click', search);
el('reset').addEventListener('click', reset);
el('export_csv').addEventListener('click', () => exportData('csv'));
el('export_xlsx').addEventListener('click', () => exportData('xlsx'));

loadFilters().then(search);
