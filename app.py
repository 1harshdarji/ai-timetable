from flask import Flask, render_template, request, jsonify
import mysql.connector
import random

app = Flask(__name__)

time_slots = [
    ("8:00", "9:00"),
    ("9:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("12:00", "1:00"),
    ("1:00", "2:00")
]

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="#yourpassword",
    database="timetable_ai"
)
cursor = db.cursor()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    subjects = data.get("subjects", [])  # subject, teacher, hours

    if not subjects:
        return jsonify({"error": "No subjects provided"})

    total_slots = len(days) * len(time_slots)

    # Build the list of subject entries based on hours
    subject_list = []
    for s in subjects:
        subject_list.extend([{'subject': s["subject"], 'teacher': s["teacher"]}] * s["hours"])

    # Fill remaining slots with blanks
    blanks_needed = total_slots - len(subject_list)
    subject_list.extend([{'subject': '-', 'teacher': '-'}] * blanks_needed)

    # fixed-length individual
    assert len(subject_list) == total_slots

    cursor.execute("DELETE FROM timetable")
    db.commit()

    POP_SIZE = 30
    GENERATIONS = 100
    MUTATION_RATE = 0.1

    def create_individual():
        individual = subject_list.copy()
        random.shuffle(individual)

        # blanks are only at beginning or end
        for day_idx in range(len(days)):
            start = day_idx * len(time_slots)
            end = start + len(time_slots)
            day_slots = individual[start:end]

            # Count blanks
            blanks = [slot for slot in day_slots if slot['subject'] == '-']
            non_blanks = [slot for slot in day_slots if slot['subject'] != '-']

            # Randomly decide if blanks go at start or end
            if random.random() < 0.5:
                day_slots = blanks + non_blanks
            else:
                day_slots = non_blanks + blanks

            # Replace back into individual
            individual[start:end] = day_slots

        return individual

    def fitness(individual):
        timetable = {day: [] for day in days}
        for i in range(total_slots):
            day = days[i // len(time_slots)]
            timetable[day].append(individual[i])

        score = 0
        for day in days:
            teachers = [slot['teacher'] for slot in timetable[day] if slot['teacher'] != '-']
            score -= len(teachers) - len(set(teachers))
        return score

    def crossover(parent1, parent2):
        point = random.randint(1, total_slots - 2)
        child = parent1[:point] + parent2[point:]
        return child

    def mutate(individual):
        if random.random() < MUTATION_RATE:
            i, j = random.sample(range(total_slots), 2)
            individual[i], individual[j] = individual[j], individual[i]
        return individual

    # Initialize population
    population = [create_individual() for _ in range(POP_SIZE)]

    # Evolution loop
    for _ in range(GENERATIONS):
        population = sorted(population, key=fitness, reverse=True)
        next_gen = population[:2]  # Elitism
        while len(next_gen) < POP_SIZE:
            parents = random.sample(population[:10], 2)
            child = crossover(parents[0], parents[1])
            child = mutate(child)
            next_gen.append(child)
        population = next_gen

    # Best timetable
    best = population[0]
    timetable = {day: [] for day in days}

    for i in range(total_slots):
        day = days[i // len(time_slots)]
        slot_idx = i % len(time_slots)
        slot_data = best[i]

        subject = f"{slot_data['subject']} ({slot_data['teacher']})" if slot_data['subject'] != '-' else '-'
        start_time, end_time = time_slots[slot_idx]

        timetable[day].append(subject)

        cursor.execute(
            "INSERT INTO timetable (day, slot, subject, start_time, end_time) VALUES (%s, %s, %s, %s, %s)",
            (day, slot_idx + 1, subject, start_time, end_time)
        )
        db.commit()

    return jsonify(timetable)

if __name__ == "__main__":
    app.run(debug=True)
