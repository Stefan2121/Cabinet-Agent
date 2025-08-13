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
  const noteInput = document.getElementById('noteInput');
  const deleteBtn = document.getElementById('deleteBtn');

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

  function openModal({ title, event }) {
    modalTitle.textContent = title;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    if (event) {
      idInput.value = event.id;
      startInput.value = event.startStr.slice(0,16);
      endInput.value = event.endStr ? event.endStr.slice(0,16) : startInput.value;
      noteInput.value = event.extendedProps?.note || '';
      // Try to preselect patient by title match (best-effort)
      for (const opt of patientSelect.options) {
        if (opt.textContent === event.title) {
          patientSelect.value = opt.value;
          break;
        }
      }
      deleteBtn.classList.remove('hidden');
    } else {
      idInput.value = '';
      noteInput.value = '';
      deleteBtn.classList.add('hidden');
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
    const payload = {
      patient_id: Number(patientSelect.value),
      start: new Date(startInput.value).toISOString(),
      end: new Date(endInput.value).toISOString(),
      note: noteInput.value || null,
    };

    try {
      if (id) {
        const { patient_id, ...updates } = payload; // patient change not supported here
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

  function defaultEnd(startDate) {
    const d = new Date(startDate.getTime());
    d.setMinutes(d.getMinutes() + 60);
    return d;
  }

  async function init() {
    await fetchPatients();

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
            const params = new URLSearchParams({ start: info.startStr, end: info.endStr });
            const res = await fetch(`/api/events?${params.toString()}`);
            const data = await res.json();
            success(data);
          } catch (err) {
            failure(err);
          }
        }
      }],
      select: async (selection) => {
        // Create new appointment
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
  }

  window.addEventListener('DOMContentLoaded', init);
})();