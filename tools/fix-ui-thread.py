"""Marshal every continuation back onto the UI thread.

CoreWebView2 can only be touched from the thread that created it. A ContinueWith that runs
on the thread pool therefore throws InvalidCastException (E_NOINTERFACE) the moment it
reads a CoreWebView2 member - which is exactly what happened: ReconcilePlayback called
ReloadPage from a continuation and the app logged a COM cast failure instead of rebuilding
the page.

The fix is not to move the work; it is to make the continuation run where it is allowed
to. Every continuation that touches the WebView is wrapped so its body executes through
BeginInvoke, and the guard against re-entrancy stays where it is.
"""

from pathlib import Path

PROGRAM = Path('LumaWall/Program.cs')
with PROGRAM.open(encoding='utf-8', newline='') as handle:
    text = handle.read()
original = text

# ── 1. ReconcilePlayback: run the whole continuation on the UI thread ────────
old = (
    "                webView.CoreWebView2.ExecuteScriptAsync(probe).ContinueWith(delegate(Task<string> task)\r\n"
    "                {\r\n"
    "                    livenessCheckInFlight = false;\r\n"
    "                    if (IsDisposed) return;\r\n"
)
new = (
    "                webView.CoreWebView2.ExecuteScriptAsync(probe).ContinueWith(delegate(Task<string> task)\r\n"
    "                {\r\n"
    "                    // Back onto the UI thread before touching anything: CoreWebView2 belongs to\r\n"
    "                    // the thread that created it, and a continuation runs on the pool. Reading a\r\n"
    "                    // CoreWebView2 member from there throws a COM cast failure rather than doing\r\n"
    "                    // the work, which is how the reconcile reported an exception instead of\r\n"
    "                    // rebuilding a page.\r\n"
    "                    if (IsDisposed) return;\r\n"
    "                    try { BeginInvoke(new Action(delegate { ReconcileOnUi(task); })); }\r\n"
    "                    catch { livenessCheckInFlight = false; }\r\n"
    "                });\r\n"
    "            }\r\n"
    "            catch (Exception ex)\r\n"
    "            {\r\n"
    "                livenessCheckInFlight = false;\r\n"
    "                AppLog.Write(\"Playback reconcile rejected on \" + screen.DeviceName + \": \" + ex.Message);\r\n"
    "            }\r\n"
    "        }\r\n"
    "\r\n"
    "        /// <summary>\r\n"
    "        /// The body of the reconcile, on the UI thread.\r\n"
    "        ///\r\n"
    "        /// Split out so the thread hop is one visible line rather than a wrapper around a\r\n"
    "        /// hundred lines of logic - the reason this exists is worth being able to see.\r\n"
    "        /// </summary>\r\n"
    "        private void ReconcileOnUi(Task<string> task)\r\n"
    "        {\r\n"
    "            livenessCheckInFlight = false;\r\n"
    "            if (IsDisposed) return;\r\n"
)
assert old in text, 'ReconcilePlayback continuation not found'
text = text.replace(old, new, 1)

# The old catch block that used to close ReconcilePlayback is now inside ReconcileOnUi, so
# the code that followed it has to be re-closed. The replacement above already wrote the
# closing brace pair, so the original tail is removed.
old_tail = (
    "                });\r\n"
    "            }\r\n"
    "            catch (Exception ex)\r\n"
    "            {\r\n"
    "                livenessCheckInFlight = false;\r\n"
    "                AppLog.Write(\"Playback reconcile rejected on \" + screen.DeviceName + \": \" + ex.Message);\r\n"
    "            }\r\n"
    "        }\r\n"
)
# Only the SECOND occurrence is the stale one - the first is the one just inserted.
first = text.find(old_tail)
second = text.find(old_tail, first + 1)
assert second > 0, 'stale tail not found'
text = text[:second] + (
    "                });\r\n"
    "            }\r\n"
    "        }\r\n"
) + text[second + len(old_tail):]

# ── 2. RequestPageState: same treatment ─────────────────────────────────────
old_state = (
    "                webView.CoreWebView2.ExecuteScriptAsync(probe)\r\n"
    "                    .ContinueWith(delegate(Task<string> task)\r\n"
    "                    {\r\n"
)
new_state = (
    "                webView.CoreWebView2.ExecuteScriptAsync(probe)\r\n"
    "                    .ContinueWith(delegate(Task<string> task)\r\n"
    "                    {\r\n"
    "                        // UI thread, for the same reason as the reconcile: this continuation\r\n"
    "                        // reads webView and screen, and CoreWebView2 is thread-affine.\r\n"
    "                        try { BeginInvoke(new Action(delegate { ReportPageState(why, hostSide, task); })); }\r\n"
    "                        catch { }\r\n"
    "                    });\r\n"
    "            }\r\n"
    "            catch (Exception ex)\r\n"
    "            {\r\n"
    "                AppLog.Write(\"Page state probe rejected on \" + screen.DeviceName + \": \" + ex.Message\r\n"
    "                    + \" [\" + hostSide + \"]\");\r\n"
    "            }\r\n"
    "        }\r\n"
    "\r\n"
    "        /// <summary>Writes the page-state probe's answer to the log, on the UI thread.</summary>\r\n"
    "        private void ReportPageState(string why, string hostSide, Task<string> task)\r\n"
    "        {\r\n"
    "            if (IsDisposed) return;\r\n"
    "            {\r\n"
)
assert old_state in text, 'RequestPageState continuation not found'
text = text.replace(old_state, new_state, 1)

# Close ReportPageState: the original block ended with a catch that logged, which is now
# handled by the caller, so the tail is trimmed to a plain close.
old_state_tail = (
    "                        AppLog.Write(\"Page state after \" + why + \" on \" + screen.DeviceName\r\n"
    "                            + \": [\" + hostSide + \"] script=\" + Truncate(value, 300));\r\n"
    "                    });\r\n"
    "            }\r\n"
    "            catch (Exception ex)\r\n"
    "            {\r\n"
    "                AppLog.Write(\"Page state probe rejected on \" + screen.DeviceName + \": \" + ex.Message\r\n"
    "                    + \" [\" + hostSide + \"]\");\r\n"
    "            }\r\n"
    "        }\r\n"
)
assert old_state_tail in text, 'RequestPageState tail not found'
text = text.replace(old_state_tail, (
    "                        AppLog.Write(\"Page state after \" + why + \" on \" + screen.DeviceName\r\n"
    "                            + \": [\" + hostSide + \"] script=\" + Truncate(value, 300));\r\n"
    "            }\r\n"
    "        }\r\n"
), 1)

with PROGRAM.open('w', encoding='utf-8', newline='') as handle:
    handle.write(text)

print('  ReconcileOnUi added:      %s' % ('private void ReconcileOnUi(' in text))
print('  ReportPageState added:    %s' % ('private void ReportPageState(' in text))
print('  BeginInvoke in reconcile: %s' % ('ReconcileOnUi(task)' in text))
print('  BeginInvoke in state:     %s' % ('ReportPageState(why, hostSide, task)' in text))
print('  bytes: %d -> %d' % (len(original), len(text)))
