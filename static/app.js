const input = document.querySelector('#photo');
const preview = document.querySelector('#photoPreview');
const placeholder = document.querySelector('#photoPlaceholder');

if (input && preview) {
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) return;
    const max = 5 * 1024 * 1024;
    if (file.size > max) {
      alert('Фотография должна быть не больше 5 МБ.');
      input.value = '';
      return;
    }
    preview.src = URL.createObjectURL(file);
    preview.classList.remove('hidden');
    if (placeholder) placeholder.classList.add('hidden');
  });
}

// Вкладки на главной
const tabs = document.querySelectorAll('.tab');
tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((t) => {
      const active = t === tab;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active);
    });
    document.querySelectorAll('.tab-panel').forEach((panel) => {
      panel.hidden = panel.dataset.panel !== tab.dataset.tab;
    });
  });
});

// Дни недели в расписании
const days = document.querySelectorAll('.day');
days.forEach((day) => {
  day.addEventListener('click', () => {
    days.forEach((d) => d.classList.toggle('active', d === day));
    document.querySelectorAll('.day-list').forEach((list) => {
      list.hidden = list.dataset.dayList !== day.dataset.day;
    });
  });
});
