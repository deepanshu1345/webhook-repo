async function fetchEvents() {
  const res = await fetch('/events');
  const data = await res.json();
  const container = document.getElementById('events');

  container.innerHTML = data.map(event => {
    const date = new Date(event.timestamp).toLocaleString('en-GB', { timeZone: 'UTC' });

    if (event.event_type === 'push') {
      return `<p>${event.author} pushed to ${event.to_branch} on ${date} UTC</p>`;
    } else if (event.event_type === 'pull_request') {
      return `<p>${event.author} submitted a pull request from ${event.from_branch} to ${event.to_branch} on ${date} UTC</p>`;
    } else if (event.event_type === 'merge_group') {
      return `<p>${event.author} merged ${event.from_branch} to ${event.to_branch} on ${date} UTC</p>`;
    } else {
      return `<p>${event.author} triggered ${event.event_type} event on ${date}</p>`;
    }
  }).join('');
}

setInterval(fetchEvents, 15000);
fetchEvents();
