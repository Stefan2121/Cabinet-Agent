(function () {
  const calendarEl = document.getElementById('calendar');
  let calendar;

  const modal = document.getElementById('appointmentModal');
  const modalTitle = document.getElementById('modalTitle');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const form = document.getElementById('appointmentForm');
  const idInput = document.getElementById('appointmentId');
  const patientSelect = document.getElementById('patientSelect');
  const startInput = document.getElementById('startInput');
  const endInput = document.getElementById('endInput');
  const serviceSelect = document.getElementById('serviceSelect');
  const noteInput = document.getElementById('noteInput');
  const deleteBtn = document.getElementById('deleteBtn');
  const sendReminderBtn = document.getElementById('sendReminderBtn');
  const doctorSelect = document.getElementById('doctorSelect');

  function isoLocal(date) {
    const pad = (n) => String(n).padStart(2, '0');
    return (
      date.getFullYear() +
      '-' + pad(date.getMonth() + 1) +
      '-' + pad(date.getDate()) +
      'T' + pad(date.getHours()) + ':' + pad(date.getMinutes())
    );
  }

  async function fetchPatients() {
    const res = await fetch('/api/patients');
    const data = await res.json();
    patientSelect.innerHTML = '';
    for (const p of data) {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.full_name;
      patientSelect.appendChild(opt);
    }
  }

  async function fetchServices() {
    const res = await fetch('/api/services');
    const data = await res.json();
    serviceSelect.innerHTML = '';
    for (const s of data) {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      serviceSelect.appendChild(opt);
    }
  }

  function openModal({ title, event }) {
    modalTitle.textContent = title;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    if (event) {
      idInput.value = event.id;
      startInput.value = event.startStr.slice(0,16);
      endInput.value = event.endStr ? event.endStr.slice(0,16) : startInput.value;
      noteInput.value = event.extendedProps?.note || '';
      serviceSelect.value = event.extendedProps?.service || 'Consult';
      // Try to preselect patient by title prefix (patient name before bullet)
      const title = event.title || '';
      const patientName = title.split('•')[0].trim();
      for (const opt of patientSelect.options) {
        if (opt.textContent === patientName) {
          patientSelect.value = opt.value;
          break;
        }
      }
      deleteBtn.classList.remove('hidden');
      sendReminderBtn.classList.remove('hidden');
    } else {
      idInput.value = '';
      noteInput.value = '';
      serviceSelect.value = 'Consult';
      deleteBtn.classList.add('hidden');
      sendReminderBtn.classList.add('hidden');
    }
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    form.reset();
  }

  closeModalBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = idInput.value;
    const doctor_id = Number(doctorSelect.value);
    const payload = {
      patient_id: Number(patientSelect.value),
      doctor_id,
      start: new Date(startInput.value).toISOString(),
      end: new Date(endInput.value).toISOString(),
      service: serviceSelect.value,
      note: noteInput.value || null,
    };

    try {
      if (id) {
        const { patient_id, doctor_id, ...updates } = payload; // no change doctor/patient here
        const res = await fetch(`/api/events/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates),
        });
        if (!res.ok) throw new Error('Eroare salvare');
      } else {
        const res = await fetch('/api/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('Eroare creare');
      }
      closeModal();
      calendar.refetchEvents();
    } catch (err) {
      alert(err.message || 'Eroare');
    }
  });

  deleteBtn.addEventListener('click', async () => {
    const id = idInput.value;
    if (!id) return;
    if (!confirm('Sigur doriți să ștergeți această programare?')) return;
    try {
      const res = await fetch(`/api/events/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Eroare ștergere');
      closeModal();
      calendar.refetchEvents();
    } catch (err) {
      alert(err.message || 'Eroare');
    }
  });

  sendReminderBtn.addEventListener('click', async () => {
    const id = idInput.value;
    if (!id) return;
    try {
      const res = await fetch(`/api/events/${id}/send_reminder`, { method: 'POST' });
      if (!res.ok) throw new Error('Trimitere eșuată');
      alert('Reminder trimis.');
    } catch (err) {
      alert(err.message || 'Eroare');
    }
  });

  function defaultEnd(startDate) {
    const d = new Date(startDate.getTime());
    d.setMinutes(d.getMinutes() + 60);
    return d;
  }

  async function init() {
    await Promise.all([fetchPatients(), fetchServices()]);

    calendar = new FullCalendar.Calendar(calendarEl, {
      locale: 'ro',
      initialView: 'dayGridMonth',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listWeek'
      },
      selectable: true,
      editable: true,
      eventSources: [{
        events: async (info, success, failure) => {
          try {
            const params = new URLSearchParams({ start: info.startStr, end: info.endStr, doctor_id: String(doctorSelect.value) });
            const res = await fetch(`/api/events?${params.toString()}`);
            const data = await res.json();
            success(data);
          } catch (err) {
            failure(err);
          }
        }
      }],
      select: async (selection) => {
        const start = new Date(selection.start);
        const end = selection.end ? new Date(selection.end) : defaultEnd(start);
        startInput.value = isoLocal(start);
        endInput.value = isoLocal(end);
        openModal({ title: 'Adaugă programare' });
      },
      eventClick: (info) => {
        const event = info.event;
        openModal({ title: 'Editează programare', event });
      },
      eventDrop: async (info) => {
        try {
          const payload = {
            start: info.event.start.toISOString(),
            end: (info.event.end || defaultEnd(info.event.start)).toISOString(),
          };
          const res = await fetch(`/api/events/${info.event.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error('Eroare reprogramare');
        } catch (err) {
          alert(err.message || 'Eroare');
          info.revert();
        }
      },
      eventResize: async (info) => {
        try {
          const payload = {
            start: info.event.start.toISOString(),
            end: info.event.end.toISOString(),
          };
          const res = await fetch(`/api/events/${info.event.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error('Eroare modificare durată');
        } catch (err) {
          alert(err.message || 'Eroare');
          info.revert();
        }
      }
    });

    calendar.render();

    doctorSelect.addEventListener('change', () => {
      calendar.refetchEvents();
    });
  }

  window.addEventListener('DOMContentLoaded', init);
})();