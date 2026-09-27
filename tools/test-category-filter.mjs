// Check the category filter the way a person uses it: pick a category, look at what appears.
//
// Why this is not the same as the catalogue checker: that one reads the file and reports
// counts. This reads the entries the filter would actually show for each category, and
// reports the titles. A catalogue can have perfect counts and still show the wrong thing,
// because the filter keys on a field that may not match what the entries hold.
//
// Each category is sampled and its titles printed, so a mismatch is visible rather than
// inferred from a number.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const catalogPath = resolve(root, "LumaWall", "catalog.json");

if (!existsSync(catalogPath)) {
  console.log(`  ${catalogPath} is missing`);
  process.exit(1);
}

const catalog = JSON.parse(readFileSync(catalogPath, "utf8"));
console.log(`  catalogue: ${catalog.length} entries`);
console.log();

// The page filters on the category field. Reproduce its rule exactly: a category matches
// when the entry's category equals it, and "All" matches everything.
const byCategory = new Map();
for (const entry of catalog) {
  const key = entry.category || "Dynamic";
  if (!byCategory.has(key)) byCategory.set(key, []);
  byCategory.get(key).push(entry);
}

const expected = [
  "Anime Loop", "Anime Girls", "Gaming", "Nature", "City", "Space", "Cars",
  "Animals", "Abstract", "Movies", "Music", "Sports", "Fantasy", "Horror",
  "Mature 18+", "Dynamic",
];

console.log("  category            entries   share   sample titles");
console.log("  " + "-".repeat(104));

let failures = 0;
for (const name of expected) {
  const entries = byCategory.get(name) || [];
  const share = ((entries.length / catalog.length) * 100).toFixed(1);
  const samples = entries.slice(0, 3).map((e) => e.title.slice(0, 24)).join(" | ");
  console.log(
    `  ${name.padEnd(20)}${String(entries.length).padStart(6)}  ${share.padStart(5)}%  ${samples}`
  );
  if (entries.length === 0) {
    console.log(`    FAIL  ${name} is empty - a filter for it shows nothing`);
    failures++;
  }
}

// An unknown category would make a filter button appear that shows nothing, or hide entries
// from every filter.
const unknown = [...byCategory.keys()].filter((k) => !expected.includes(k));
if (unknown.length) {
  console.log();
  console.log(`  FAIL  ${unknown.length} categor(ies) are not in the filter list: ${unknown.join(", ")}`);
  failures++;
}

// The categories the app offers must all exist in the data, or a button is dead.
const missing = expected.filter((k) => !byCategory.has(k));
if (missing.length) {
  console.log();
  console.log(`  FAIL  the filter offers ${missing.join(", ")} but no entry has it`);
  failures++;
}

// A category whose entries are mostly the same title is a category filled by a rule that
// matched one thing.
console.log();
for (const name of expected) {
  const entries = byCategory.get(name) || [];
  if (entries.length < 20) continue;
  const unique = new Set(entries.map((e) => e.title)).size;
  if (unique < entries.length * 0.5) {
    console.log(`  FAIL  ${name}: only ${unique} distinct titles among ${entries.length} entries`);
    failures++;
  }
}

console.log();
if (failures) {
  console.log(`  ${failures} problem(s) found.`);
  process.exit(1);
}
console.log("  OK    every category has entries, a distinct set of titles, and is in the filter list.");
