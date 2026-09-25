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

// Проверка email при регистрации
const regEmail = document.querySelector('#regEmail');
if (regEmail) {
  const emailError = document.querySelector('#emailError');
  const submit = document.querySelector('#regSubmit');
  let timer;

  const showError = (text) => {
    emailError.textContent = text;
    emailError.hidden = !text;
    regEmail.classList.toggle('invalid', Boolean(text));
    submit.disabled = Boolean(text);
  };

  const check = async () => {
    const email = regEmail.value.trim();
    if (!email || !regEmail.checkValidity()) return showError('');
    try {
      const res = await fetch(`${regEmail.dataset.checkUrl}?email=${encodeURIComponent(email)}`);
      const data = await res.json();
      if (regEmail.value.trim() === email) {
        showError(data.taken ? 'Пользователь с таким email уже существует.' : '');
      }
    } catch {
      showError('');
    }
  };

  regEmail.addEventListener('input', () => {
    clearTimeout(timer);
    showError('');
    timer = setTimeout(check, 400);
  });
  regEmail.addEventListener('blur', check);
}
