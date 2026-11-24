
document.addEventListener("DOMContentLoaded", function () {

    // CHILD PROFILE FORM

    const childForm = document.getElementById("childForm");

    if (childForm) {
        childForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const data = Object.fromEntries(new FormData(childForm));

            try {
                await apiRequest("/api/children", "POST", data);
                alert("Child profile added successfully!");
                location.reload();
            } catch (error) {
                alert(error.message);
            }
        });
    }


    // SCHEDULE FORM

    const scheduleForm = document.getElementById("scheduleForm");

    if (scheduleForm) {
        scheduleForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const data = Object.fromEntries(new FormData(scheduleForm));

            try {
                await apiRequest("/api/schedules", "POST", data);
                alert("Schedule created successfully!");
                scheduleForm.reset();
                loadSchedules();
            } catch (error) {
                alert(error.message);
            }
        });

        loadSchedules();
    }


    // TASK FORM

    const taskForm = document.getElementById("taskForm");

    if (taskForm) {
        taskForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const data = Object.fromEntries(new FormData(taskForm));

            try {
                await apiRequest("/api/tasks", "POST", data);
                alert("Activity added successfully!");
                taskForm.reset();
                loadTasks();
            } catch (error) {
                alert(error.message);
            }
        });

        loadTasks();
    }


    // COMMUNICATION BOARD FORM

    const communicationForm =
        document.getElementById("communicationForm");

    if (communicationForm) {
        communicationForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const data = Object.fromEntries(new FormData(communicationForm));

            try {
                await apiRequest(
                    "/api/communication-cards",
                    "POST",
                    data
                );

                alert("Communication card added!");
                communicationForm.reset();
                loadCommunicationCards();

            } catch (error) {
                alert(error.message);
            }
        });

        loadCommunicationCards();
    }


    // PROGRESS

    if (document.getElementById("progressTable")) {
        loadProgress();
    }


    // SETTINGS

    const settingsForm = document.getElementById("settingsForm");

    if (settingsForm) {

        settingsForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const formData = new FormData(settingsForm);

            const data = {
                speech_enabled: formData.has("speech_enabled"),
                notification_enabled: formData.has("notification_enabled"),
                theme: formData.get("theme")
            };

            try {
                await apiRequest("/api/settings", "PUT", data);

                applyTheme(data.theme);

                alert("Settings saved successfully!");

            } catch (error) {
                alert(error.message);
            }
        });

    }

    // LOAD SAVED THEME

    loadSavedTheme();

});


// -----------------------------
// LOAD SCHEDULES
// -----------------------------

async function loadSchedules() {

    const select = document.getElementById("scheduleSelect");

    if (!select) return;

    try {

        const schedules = await apiRequest("/api/schedules");

        select.replaceChildren();

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose a schedule";
        select.appendChild(placeholder);

        schedules.forEach(schedule => {

            const option = document.createElement("option");

            option.value = schedule.id;
            option.textContent =
                `${schedule.title} - ${schedule.child_name} (${schedule.schedule_date})`;

            select.appendChild(option);

        });

    } catch (error) {
        select.textContent = error.message;
    }

}


// -----------------------------
// LOAD TASKS
// -----------------------------

async function loadTasks() {

    const table = document.getElementById("taskTable");

    if (!table) return;

    try {

        const tasks = await apiRequest("/api/tasks");

        table.replaceChildren();

        if (tasks.length === 0) {
            table.innerHTML =
                '<tr><td colspan="6">No activities found.</td></tr>';
            return;
        }

        tasks.forEach(task => {

            const row = document.createElement("tr");

            const activity = document.createElement("td");
            activity.textContent = task.title;

            const schedule = document.createElement("td");
            schedule.textContent = task.schedule_title;

            const time = document.createElement("td");
            time.textContent =
                `${task.start_time || "--"} - ${task.end_time || "--"}`;

            const category = document.createElement("td");
            category.textContent = task.category || "General";

            const status = document.createElement("td");
            status.textContent = task.status;

            const action = document.createElement("td");

            if (task.status !== "Completed") {

                const button = document.createElement("button");
                button.className = "btn btn-sm btn-success";
                button.textContent = "Complete";

                button.addEventListener("click", () => {
                    completeTask(task.id, button);
                });

                action.appendChild(button);

            } else {
                action.textContent = "✓";
            }

            [activity, schedule, time, category, status, action]
                .forEach(cell => row.appendChild(cell));

            table.appendChild(row);

        });

    } catch (error) {
        table.textContent = error.message;
    }

}


// -----------------------------
// COMPLETE TASK
// -----------------------------

async function completeTask(taskId, button) {

    try {

        await apiRequest(
            `/api/tasks/${taskId}/complete`,
            "POST",
            {}
        );

        if (button) {
            button.textContent = "Completed";
            button.disabled = true;
            button.className = "btn btn-sm btn-success";
        }

        loadTasks();

    } catch (error) {
        alert(error.message);
    }

}


// -----------------------------
// DELETE CHILD
// -----------------------------

async function deleteChild(childId) {

    if (!confirm("Are you sure you want to delete this child profile and its related records?")) {
        return;
    }

    try {

        await apiRequest(
            `/api/children/${childId}`,
            "DELETE"
        );

        alert("Child profile deleted.");
        location.reload();

    } catch (error) {
        alert(error.message);
    }

}


// -----------------------------
// COMMUNICATION BOARD
// -----------------------------

async function loadCommunicationCards() {

    const container = document.getElementById("communicationCards");

    if (!container) return;

    try {

        const cards = await apiRequest("/api/communication-cards");

        container.replaceChildren();

        if (cards.length === 0) {
            container.textContent = "No communication cards yet.";
            return;
        }

        const emojis = {
            Needs: "💧",
            Feelings: "😊",
            Activities: "🎨",
            People: "👨‍👩‍👧",
            Places: "🏠"
        };

        cards.forEach(card => {

            const column = document.createElement("div");
            column.className = "col-6 col-md-4 col-xl-3";

            const button = document.createElement("button");
            button.className = "communication-card";

            const emoji = document.createElement("span");
            emoji.className = "emoji";
            emoji.textContent = emojis[card.category] || "⭐";

            const title = document.createElement("strong");
            title.textContent = card.title;

            const speak = document.createElement("div");
            speak.className = "text-muted small mt-2";
            speak.textContent = "Tap to speak";

            button.append(emoji, title, speak);

            button.addEventListener("click", () => {
                speakText(card.speech_text || card.title);
            });

            button.addEventListener("contextmenu", async event => {
                event.preventDefault();

                if (!confirm(`Delete ${card.title}?`)) return;

                try {
                    await apiRequest(
                        `/api/communication-cards/${card.id}`,
                        "DELETE"
                    );

                    loadCommunicationCards();

                } catch (error) {
                    alert(error.message);
                }
            });

            column.appendChild(button);
            container.appendChild(column);

        });

    } catch (error) {
        container.textContent = error.message;
    }

}


// -----------------------------
// TEXT TO SPEECH
// -----------------------------

async function speakText(text) {

    try {

        const settings = await apiRequest("/api/settings");

        if (!settings.speech_enabled) {
            return;
        }

        if (!("speechSynthesis" in window)) {
            alert("Text-to-speech is not supported by this browser.");
            return;
        }

        window.speechSynthesis.cancel();

        const speech = new SpeechSynthesisUtterance(text);

        speech.lang = "en-US";
        speech.rate = 0.9;
        speech.pitch = 1;

        window.speechSynthesis.speak(speech);

    } catch (error) {
        alert(error.message);
    }

}


// -----------------------------
// THEME SETTINGS
// -----------------------------

function applyTheme(theme) {

    document.body.classList.remove("light-theme", "dark-theme");

    document.body.classList.add(
        theme === "dark" ? "dark-theme" : "light-theme"
    );

}


async function loadSavedTheme() {

    try {

        const settings = await apiRequest("/api/settings");

        applyTheme(settings.theme || "light");

    } catch (error) {
        console.error("Unable to load saved theme:", error);
    }

}


// -----------------------------
// PROGRESS TRACKING
// -----------------------------

let progressChartInstance = null;

async function loadProgress() {

    const table = document.getElementById("progressTable");

    if (!table) return;

    try {

        const records = await apiRequest("/api/progress");

        table.replaceChildren();

        const names = [];
        const completedData = [];
        const pendingData = [];

        records.forEach(record => {

            const total = Number(record.total_tasks);
            const completed = Number(record.completed_tasks);
            const pending = Math.max(0, total - completed);

            const percentage = total > 0
                ? Math.round((completed / total) * 100)
                : 0;

            const row = document.createElement("tr");

            const name = document.createElement("td");
            name.textContent = record.child_name;

            const totalCell = document.createElement("td");
            totalCell.textContent = total;

            const completedCell = document.createElement("td");
            completedCell.textContent = completed;

            const progressCell = document.createElement("td");

            const progress = document.createElement("div");
            progress.className = "progress";
            progress.style.height = "10px";

            const bar = document.createElement("div");
            bar.className = "progress-bar bg-success";
            bar.style.width = percentage + "%";

            progress.appendChild(bar);

            const label = document.createElement("small");
            label.textContent = percentage + "%";
            label.className = "text-muted";

            progressCell.append(progress, label);

            [name, totalCell, completedCell, progressCell]
                .forEach(cell => row.appendChild(cell));

            table.appendChild(row);

            names.push(record.child_name);
            completedData.push(completed);
            pendingData.push(pending);

        });

        if (typeof Chart !== "undefined") {

            const canvas = document.getElementById("progressChart");

            if (canvas) {

                if (progressChartInstance) {
                    progressChartInstance.destroy();
                }

                progressChartInstance = new Chart(canvas, {
                    type: "bar",
                    data: {
                        labels: names,
                        datasets: [
                            {
                                label: "Completed",
                                data: completedData,
                                backgroundColor: "#22a06b"
                            },
                            {
                                label: "Remaining",
                                data: pendingData,
                                backgroundColor: "#e5a64d"
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });

            }

        }

        if (records.length === 0) {
            table.innerHTML =
                '<tr><td colspan="4">No progress records available.</td></tr>';
        }

    } catch (error) {
        table.textContent = error.message;
    }

}


// -----------------------------
// ACTIVITY TIMER
// -----------------------------

let timerSeconds = 300;
let timerInterval = null;

function updateTimerDisplay() {

    const display = document.getElementById("timerDisplay");

    if (!display) return;

    const minutes = Math.floor(timerSeconds / 60);
    const seconds = timerSeconds % 60;

    display.textContent =
        String(minutes).padStart(2, "0") + ":" +
        String(seconds).padStart(2, "0");

}


function startTimer() {

    if (timerInterval) return;

    timerInterval = setInterval(() => {

        if (timerSeconds > 0) {

            timerSeconds--;
            updateTimerDisplay();

        } else {

            clearInterval(timerInterval);
            timerInterval = null;

            alert("Time is up!");

        }

    }, 1000);

}


function resetTimer() {

    clearInterval(timerInterval);
    timerInterval = null;

    timerSeconds = 300;

    updateTimerDisplay();

}
