// ============================================================
// Smart Event Analytics Agent — Semester Data
// Last Semester: Jan 2026 – May 2026
// ============================================================

const SEMESTER = {
  name: "Spring 2026",
  start: "2026-01-15",
  end:   "2026-05-30"
};

// Feedback score array: each element is a student rating 1–5
// null values simulate missing/incomplete feedback forms
const CLUBS = [
  {
    id: "codecraft",
    name: "CodeCraft",
    tagline: "Competitive Programming & DSA",
    color: "#7c3aed",
    icon: "⚡",
    events: [
      {
        id: "cc1",
        name: "DSA Bootcamp",
        type: "Workshop",
        date: "2026-01-22",
        registrations: 120,
        attendance: 108,
        feedback: [4,5,5,4,5,3,4,5,4,4,5,5,4,3,5,4,5,4,4,5,5,4,4,5,3,4,5,5,4,4],
        speaker_rating: 4.7,
        duration_hours: 6,
        resources_used: 850
      },
      {
        id: "cc2",
        name: "Hackathon 3.0",
        type: "Hackathon",
        date: "2026-02-14",
        registrations: 200,
        attendance: 188,
        feedback: [5,5,4,5,5,5,4,5,5,5,4,4,5,5,5,4,5,5,3,5,5,4,5,5,4,5,5,5,4,5,5,5,4,5,5,5,4,4,5],
        speaker_rating: 4.9,
        duration_hours: 24,
        resources_used: 2200
      },
      {
        id: "cc3",
        name: "LeetCode Weekly Grind",
        type: "Practice Session",
        date: "2026-03-08",
        registrations: 80,
        attendance: null, // missing — no entry tracking done
        feedback: [4,4,3,5,4,4,5,3,4,4,4,5,4,3,4],
        speaker_rating: 4.1,
        duration_hours: 3,
        resources_used: 100
      },
      {
        id: "cc4",
        name: "Inter-College Code War",
        type: "Competition",
        date: "2026-04-20",
        registrations: 150,
        attendance: 142,
        feedback: [5,5,5,4,5,4,5,5,4,5,5,5,4,5,5,5,4,5,5,4,5,5,5,4,5],
        speaker_rating: 4.8,
        duration_hours: 8,
        resources_used: 1800
      }
    ]
  },
  {
    id: "robotech",
    name: "RoboTech",
    tagline: "Robotics & Embedded Systems",
    color: "#0891b2",
    icon: "🤖",
    events: [
      {
        id: "rt1",
        name: "Arduino Workshop",
        type: "Workshop",
        date: "2026-01-28",
        registrations: 90,
        attendance: 85,
        feedback: [4,5,4,4,5,4,3,4,5,4,4,4,3,5,4,4,5,4,4,3],
        speaker_rating: 4.4,
        duration_hours: 5,
        resources_used: 1200
      },
      {
        id: "rt2",
        name: "Bot Brawl Championship",
        type: "Competition",
        date: "2026-02-22",
        registrations: 60,
        attendance: 55,
        feedback: [5,4,5,5,4,4,5,4,5,5,4,5,4,5,5,4,4,5],
        speaker_rating: 4.6,
        duration_hours: 10,
        resources_used: 3000
      },
      {
        id: "rt3",
        name: "Drone Racing Demo",
        type: "Demo",
        date: "2026-03-15",
        registrations: 110,
        attendance: 98,
        feedback: null, // feedback forms lost
        speaker_rating: 4.5,
        duration_hours: 3,
        resources_used: 500
      },
      {
        id: "rt4",
        name: "IoT Summit",
        type: "Seminar",
        date: "2026-05-10",
        registrations: 75,
        attendance: 60,
        feedback: [3,4,3,4,4,3,3,4,4,3,4,4,3,3,4],
        speaker_rating: 3.9,
        duration_hours: 4,
        resources_used: 700
      }
    ]
  },
  {
    id: "cybershield",
    name: "CyberShield",
    tagline: "Cybersecurity & Ethical Hacking",
    color: "#dc2626",
    icon: "🛡️",
    events: [
      {
        id: "cs1",
        name: "CTF Beginners Edition",
        type: "Competition",
        date: "2026-02-01",
        registrations: 95,
        attendance: 90,
        feedback: [5,4,5,5,4,5,5,4,5,5,5,4,5,5,4,5,5,4,5,5],
        speaker_rating: 4.8,
        duration_hours: 8,
        resources_used: 600
      },
      {
        id: "cs2",
        name: "Kali Linux Deep Dive",
        type: "Workshop",
        date: "2026-03-05",
        registrations: 70,
        attendance: 65,
        feedback: [4,5,4,4,5,4,5,4,4,5,4,5,4,4,5],
        speaker_rating: 4.6,
        duration_hours: 6,
        resources_used: 400
      },
      {
        id: "cs3",
        name: "Cyber Hygiene Talk",
        type: "Seminar",
        date: "2026-04-08",
        registrations: 130,
        attendance: 118,
        feedback: [4,4,3,5,4,4,5,3,4,4,4,3,4,4,5,4,3,4,4,5,4,4,3,4,4,4,4,5,4,4],
        speaker_rating: 4.3,
        duration_hours: 2,
        resources_used: 200
      },
      {
        id: "cs4",
        name: "Advanced CTF Finals",
        type: "Competition",
        date: "2026-05-18",
        registrations: 50,
        attendance: 48,
        feedback: [5,5,5,4,5,5,5,5,4,5,5,5,4,5,5],
        speaker_rating: 4.9,
        duration_hours: 12,
        resources_used: 900
      }
    ]
  },
  {
    id: "dataminds",
    name: "DataMinds",
    tagline: "Data Science & Machine Learning",
    color: "#059669",
    icon: "📊",
    events: [
      {
        id: "dm1",
        name: "Python for Data Science",
        type: "Workshop",
        date: "2026-01-30",
        registrations: 140,
        attendance: 125,
        feedback: [4,5,4,4,5,4,3,4,5,4,4,4,3,5,4,4,5,4,4,3,4,5,4,4,5],
        speaker_rating: 4.5,
        duration_hours: 8,
        resources_used: 500
      },
      {
        id: "dm2",
        name: "Kaggle Hackathon Prep",
        type: "Workshop",
        date: "2026-02-20",
        registrations: 85,
        attendance: 70,
        feedback: [3,4,3,4,4,3,3,4,4,3,4,4,3,3,4,3,4,3,4,4],
        speaker_rating: 3.8,
        duration_hours: 5,
        resources_used: 300
      },
      {
        id: "dm3",
        name: "ML Model Showdown",
        type: "Competition",
        date: "2026-03-28",
        registrations: 100,
        attendance: null, // online event, no attendance tracked
        feedback: [4,5,5,4,5,4,5,5,4,4,5,4,5,5,4,5,5,4,4,5],
        speaker_rating: 4.7,
        duration_hours: 6,
        resources_used: 200
      },
      {
        id: "dm4",
        name: "AI Ethics Panel",
        type: "Seminar",
        date: "2026-05-05",
        registrations: 180,
        attendance: 160,
        feedback: [4,4,5,4,4,5,4,4,5,4,4,4,5,4,4,5,4,4,5,4,4,4,5,4,4,5,4,4,4,5],
        speaker_rating: 4.6,
        duration_hours: 3,
        resources_used: 300
      }
    ]
  },
  {
    id: "cloudnine",
    name: "CloudNine",
    tagline: "Cloud Computing & DevOps",
    color: "#d97706",
    icon: "☁️",
    events: [
      {
        id: "cn1",
        name: "AWS Fundamentals",
        type: "Workshop",
        date: "2026-02-10",
        registrations: 110,
        attendance: 88,
        feedback: [3,4,3,3,4,3,4,4,3,3,4,3,3,4,3,3,4,3,4,4],
        speaker_rating: 3.7,
        duration_hours: 6,
        resources_used: 800
      },
      {
        id: "cn2",
        name: "Docker & Kubernetes Crash Course",
        type: "Workshop",
        date: "2026-03-18",
        registrations: 75,
        attendance: 60,
        feedback: [4,3,4,4,3,4,3,4,4,3,4,4,3,4,4],
        speaker_rating: 4.0,
        duration_hours: 7,
        resources_used: 600
      },
      {
        id: "cn3",
        name: "Cloud Build Challenge",
        type: "Competition",
        date: "2026-04-14",
        registrations: 55,
        attendance: 40,
        feedback: [3,3,4,3,3,4,3,3,4,3,3,3],
        speaker_rating: 3.5,
        duration_hours: 8,
        resources_used: 1000
      },
      {
        id: "cn4",
        name: "DevOps Culture Talk",
        type: "Seminar",
        date: "2026-05-20",
        registrations: 90,
        attendance: null,  // speaker cancelled, partial event
        feedback: null,
        speaker_rating: null,
        duration_hours: 2,
        resources_used: 150
      }
    ]
  },
  {
    id: "designlab",
    name: "DesignLab",
    tagline: "UI/UX Design & Product Thinking",
    color: "#db2777",
    icon: "🎨",
    events: [
      {
        id: "dl1",
        name: "Figma Masterclass",
        type: "Workshop",
        date: "2026-01-25",
        registrations: 95,
        attendance: 90,
        feedback: [5,5,4,5,5,4,5,5,4,5,5,4,5,5,5,4,5,5,4,5],
        speaker_rating: 4.8,
        duration_hours: 5,
        resources_used: 300
      },
      {
        id: "dl2",
        name: "Design Thinking Sprint",
        type: "Workshop",
        date: "2026-02-28",
        registrations: 70,
        attendance: 68,
        feedback: [4,5,5,4,5,5,4,5,5,4,5,4,5,5,4,5,4,5],
        speaker_rating: 4.7,
        duration_hours: 8,
        resources_used: 500
      },
      {
        id: "dl3",
        name: "UX Research Symposium",
        type: "Seminar",
        date: "2026-04-02",
        registrations: 60,
        attendance: 52,
        feedback: [4,4,5,4,4,5,4,4,4,5,4,4,5,4,4],
        speaker_rating: 4.4,
        duration_hours: 3,
        resources_used: 200
      },
      {
        id: "dl4",
        name: "UI Redesign Challenge",
        type: "Competition",
        date: "2026-05-25",
        registrations: 80,
        attendance: 75,
        feedback: [5,5,4,5,5,5,4,5,5,4,5,5,5,4,5,5,4,5,5,5],
        speaker_rating: 4.9,
        duration_hours: 6,
        resources_used: 400
      }
    ]
  }
];

// Export
if (typeof module !== 'undefined') module.exports = { CLUBS, SEMESTER };
