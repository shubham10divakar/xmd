// Medium Node.js script — word frequency analysis + grade classifier

// ── Word frequency ──────────────────────────────────────────────────────────
const text = "the quick brown fox jumps over the lazy dog the fox and the dog";
const words = text.split(" ");
const freq = new Map();
words.forEach(w => freq.set(w, (freq.get(w) || 0) + 1));

console.log("=== Node.js: Word Frequency ===");
console.log(`Text   : "${text}"`);
console.log(`Words  : ${words.length}  Unique: ${freq.size}\n`);
console.log("Top words:");
[...freq.entries()]
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5)
  .forEach(([w, c]) => {
    const bar = "#".repeat(c);
    console.log(`  ${w.padEnd(8)} ${bar} (${c})`);
  });

// ── Grade classifier ────────────────────────────────────────────────────────
const students = [
  { name: "Alice", score: 94 },
  { name: "Bob",   score: 72 },
  { name: "Carol", score: 88 },
  { name: "Dave",  score: 61 },
  { name: "Eve",   score: 79 },
];

const grade = s => s >= 90 ? "A" : s >= 80 ? "B" : s >= 70 ? "C" : "F";
const avg = students.reduce((a, s) => a + s.score, 0) / students.length;

console.log("\n=== Grade Classifier ===");
students
  .sort((a, b) => b.score - a.score)
  .forEach(s => console.log(`  ${s.name.padEnd(8)} ${s.score}  ${grade(s.score)}`));
console.log(`\n  Average: ${avg.toFixed(1)}`);
console.log(`  Passing: ${students.filter(s => s.score >= 70).length}/${students.length}`);
