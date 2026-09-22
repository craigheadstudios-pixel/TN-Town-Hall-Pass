const CATEGORY_LABELS = {
  county_commission: "County Commission",
  city_council: "City / Town Council",
  school_board: "School Board",
  other: "Other",
};

const state = {
  data: null,
  county: "",
  category: "",
  search: "",
};

async function loadData() {
  const statusLine = document.getElementById("status-line");
  try {
    const res = await fetch("data/meetings.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.data = await res.json();
  } catch (err) {
    statusLine.textContent =
      "Couldn't load meeting data. If you're running this locally, run `python3 -m scraper.run` first to generate site/data/meetings.json.";
    console.error(err);
    return;
  }
  populateCountyFilter();
  render();
}

function populateCountyFilter() {
  const select = document.getElementById("county-filter");
  for (const county of state.data.counties) {
    const opt = document.createElement("option");
    opt.value = county;
    opt.textContent = county;
    select.appendChild(opt);
  }
}

function formatDateHeading(date) {
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatTime(date) {
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function googleCalendarUrl(meeting) {
  const start = new Date(meeting.start);
  const end = meeting.end ? new Date(meeting.end) : new Date(start.getTime() + 60 * 60 * 1000);
  const fmt = (d) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `${meeting.jurisdiction} — ${meeting.body}`,
    dates: `${fmt(start)}/${fmt(end)}`,
    details: [meeting.title, meeting.agenda_url ? `Agenda: ${meeting.agenda_url}` : "", meeting.source_url ? `Source: ${meeting.source_url}` : ""]
      .filter(Boolean)
      .join("\n"),
    location: meeting.location || "",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function jurisdictionFeed(meeting) {
  return state.data.jurisdictions.find((j) => j.source_id === meeting.source_id)?.feed;
}

function matchesFilters(meeting) {
  if (state.county && meeting.county !== state.county) return false;
  if (state.category && meeting.category !== state.category) return false;
  if (state.search) {
    const haystack = `${meeting.jurisdiction} ${meeting.body} ${meeting.title}`.toLowerCase();
    if (!haystack.includes(state.search.toLowerCase())) return false;
  }
  return true;
}

function render() {
  const list = document.getElementById("meeting-list");
  const statusLine = document.getElementById("status-line");
  list.innerHTML = "";

  const meetings = state.data.meetings.filter(matchesFilters);

  const countyWrap = document.getElementById("subscribe-county-wrap");
  const countyLink = document.getElementById("subscribe-county");
  if (state.county) {
    countyLink.href = `feeds/counties/${slugify(state.county)}.ics`;
    countyLink.textContent = `${state.county} County only`;
    countyWrap.hidden = false;
  } else {
    countyWrap.hidden = true;
  }

  const generatedAt = state.data.generated_at ? new Date(state.data.generated_at) : null;
  const generatedNote = generatedAt ? ` · data last refreshed ${generatedAt.toLocaleString()}` : "";

  if (meetings.length === 0) {
    statusLine.textContent = `No meetings match your filters${generatedNote}.`;
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent =
      state.data.meeting_count === 0
        ? "No meetings loaded yet — sources are still being confirmed. See docs/COVERAGE.md on GitHub for status."
        : "No meetings match the current filters.";
    list.appendChild(empty);
    return;
  }

  statusLine.textContent = `${meetings.length} meeting${meetings.length === 1 ? "" : "s"}${generatedNote}`;

  let currentDateKey = null;
  let currentGroup = null;

  for (const meeting of meetings) {
    const start = new Date(meeting.start);
    const dateKey = start.toDateString();
    if (dateKey !== currentDateKey) {
      currentDateKey = dateKey;
      currentGroup = document.createElement("div");
      currentGroup.className = "meeting-group";
      const heading = document.createElement("h2");
      heading.textContent = formatDateHeading(start);
      currentGroup.appendChild(heading);
      list.appendChild(currentGroup);
    }

    const card = document.createElement("div");
    card.className = "meeting-card";

    const metaRow = document.createElement("div");
    metaRow.className = "meta-row";
    const when = document.createElement("span");
    when.className = "when";
    when.textContent = formatTime(start);
    metaRow.appendChild(when);
    const tag = document.createElement("span");
    tag.className = `tag ${meeting.category}`;
    tag.textContent = CATEGORY_LABELS[meeting.category] || meeting.category;
    metaRow.appendChild(tag);
    card.appendChild(metaRow);

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `${meeting.jurisdiction} — ${meeting.body}`;
    card.appendChild(title);

    if (meeting.location) {
      const location = document.createElement("div");
      location.className = "location";
      location.textContent = meeting.location;
      card.appendChild(location);
    }

    const actions = document.createElement("div");
    actions.className = "actions";

    const feed = jurisdictionFeed(meeting);
    if (feed) {
      const subscribeLink = document.createElement("a");
      subscribeLink.className = "btn";
      subscribeLink.href = feed;
      subscribeLink.textContent = "Subscribe to this jurisdiction";
      actions.appendChild(subscribeLink);
    }

    const gcalLink = document.createElement("a");
    gcalLink.className = "btn";
    gcalLink.href = googleCalendarUrl(meeting);
    gcalLink.target = "_blank";
    gcalLink.rel = "noopener";
    gcalLink.textContent = "Add to Google Calendar";
    actions.appendChild(gcalLink);

    if (meeting.agenda_url) {
      const agendaLink = document.createElement("a");
      agendaLink.className = "btn";
      agendaLink.href = meeting.agenda_url;
      agendaLink.target = "_blank";
      agendaLink.rel = "noopener";
      agendaLink.textContent = "Agenda";
      actions.appendChild(agendaLink);
    }

    card.appendChild(actions);
    currentGroup.appendChild(card);
  }
}

function slugify(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

document.getElementById("county-filter").addEventListener("change", (e) => {
  state.county = e.target.value;
  render();
});
document.getElementById("category-filter").addEventListener("change", (e) => {
  state.category = e.target.value;
  render();
});
document.getElementById("search").addEventListener("input", (e) => {
  state.search = e.target.value;
  render();
});

loadData();
