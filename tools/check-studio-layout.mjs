// Fails when the Luma Studio page's two columns are badly out of balance.
//
// Why: the page shipped with the left column 746px shorter than the right one, which left
// a band of empty background under the presets. Nobody noticed because the build was clean
// and nothing threw - it was a layout fault, and layout faults need a measurement.
//
// ── why this reads a file instead of an exit code ────────────────────────────────
//
// tools/MeasureStudioLayout.exe is a WPF program. A WPF Application that has shown a
// Window does not reliably hand its exit code back to the shell: the tool returned 1 for
// an out-of-balance page and the caller saw 127, which reads as "command not found" from a
// run that had in fact worked.
//
// So the tool writes its verdict to build/studio-layout.json and this reads that. The
// answer is the tool's own either way - there is no second opinion to reconcile.

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, unlinkSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const tool = resolve(root, 'tools', 'bin', 'MeasureStudioLayout.exe');
const app = resolve(root, 'LumaWall', 'bin', 'Release', 'LumaWall.exe');
const result = resolve(root, 'build', 'studio-layout.json');

if (!existsSync(app)) {
  console.log('  the app is not built, so the page cannot be measured');
  console.log('  run tools/build_app.ps1 first');
  process.exit(1);
}

if (!existsSync(tool)) {
  console.log('  the measuring tool is not built:');
  console.log('    MSBuild tools/measure-studio-layout.csproj /p:Configuration=Release /p:Platform=x64');
  process.exit(1);
}

// A stale result would let a previous pass hide a current failure, so it is removed
// before the run - and its absence afterwards is itself a failure.
if (existsSync(result)) unlinkSync(result);

try {
  const printed = execFileSync(tool, [result], { encoding: 'utf8', timeout: 120000 });
  process.stdout.write(printed);
} catch (error) {
  // A throw here is not a verdict - the verdict is the file. Print whatever came out and
  // fall through to reading it, so a strange shell exit code does not become the answer.
  if (error.stdout) process.stdout.write(error.stdout);
  if (!existsSync(result) && error.status === undefined) {
    console.log('  the measuring tool could not be run: ' + error.message);
    process.exit(1);
  }
}

if (!existsSync(result)) {
  console.log('  the measuring tool did not write ' + result);
  console.log('  it ran but produced no verdict, so there is nothing to check');
  process.exit(1);
}

let report;
try {
  report = JSON.parse(readFileSync(result, 'utf8'));
} catch (error) {
  console.log('  the measuring tool wrote a result that cannot be read: ' + error.message);
  process.exit(1);
}

console.log('');
console.log(
  '  left ' + report.leftContent + 'px  vs  right ' + report.rightContent +
  'px   difference ' + report.difference + 'px  (limit ' + report.limit + 'px)'
);

if (!report.balanced) {
  console.log('');
  console.log('  the columns are ' + report.difference + 'px apart, which reads as an unfinished page');
  console.log('  move a card between the columns, or change what the columns hold');
  process.exit(1);
}

console.log('  the two columns are balanced');
process.exit(0);
