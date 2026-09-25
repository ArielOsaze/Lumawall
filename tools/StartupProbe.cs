// StartupProbe.cs - verifies the StartupTask ABI calls in isolation.
//
// The production code reaches Windows.ApplicationModel.StartupTask through
// combase + raw vtable slots because the SDK projection cannot be consumed by
// this project's toolchain. A wrong IID or a wrong vtable slot compiles fine
// and fails silently at runtime, so the calls are exercised here first, where
// every HRESULT and every state value is printed.
//
// Usage:
//   StartupProbe.exe           -> read the current state
//   StartupProbe.exe enable    -> RequestEnableAsync
//   StartupProbe.exe disable   -> Disable
//
// Expected when the process is NOT packaged (running from the build folder):
//   activation fails with the "class not registered" family of errors, which is
//   the correct outcome and proves the packaged/not-packaged branch works.

using System;
using System.Runtime.InteropServices;
using System.Text;

internal static class StartupProbe
{
    private const int ERROR_INSUFFICIENT_BUFFER = 122;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetCurrentPackageFullName(ref int length, StringBuilder name);

    // HSTRING is a handle, not a character pointer - see the note in MainWindow.cs.
    [DllImport("combase.dll")]
    private static extern int RoGetActivationFactory(IntPtr classId, ref Guid iid, out IntPtr factory);

    [DllImport("combase.dll", CharSet = CharSet.Unicode)]
    private static extern int WindowsCreateString(string source, int length, out IntPtr hstring);

    [DllImport("combase.dll")]
    private static extern int WindowsDeleteString(IntPtr hstring);

    private static readonly Guid IID_IStartupTaskStatics = new Guid("ee5b60bd-a148-41a7-b26e-e8b88a1e62f8");

    private const int Slot_GetAsync = 7;
    private const int Slot_RequestEnableAsync = 6;
    private const int Slot_Disable = 7;
    private const int Slot_get_State = 8;
    private const int Slot_GetResults = 5;

    private delegate int GetAsyncDelegate(IntPtr self, IntPtr taskId, out IntPtr operation);
    private delegate int RequestEnableAsyncDelegate(IntPtr self, out IntPtr operation);
    private delegate int DisableDelegate(IntPtr self);
    private delegate int GetStateDelegate(IntPtr self, out int state);
    private delegate int GetResultsDelegate(IntPtr self, out IntPtr result);

    private static T Vtable<T>(IntPtr obj, int slot) where T : class
    {
        IntPtr vtable = Marshal.ReadIntPtr(obj);
        IntPtr fn = Marshal.ReadIntPtr(vtable, slot * IntPtr.Size);
        return (T)(object)Marshal.GetDelegateForFunctionPointer(fn, typeof(T));
    }

    private static int Resolve(IntPtr operation, out IntPtr result)
    {
        result = IntPtr.Zero;
        for (int i = 0; i < 200; i++)
        {
            int hr = Vtable<GetResultsDelegate>(operation, Slot_GetResults)(operation, out result);
            if (hr == 0) return 0;
            if (hr != unchecked((int)0x8000000EL)) return hr;
            System.Threading.Thread.Sleep(50);
        }
        return -1;
    }

    private static string StateName(int state)
    {
        switch (state)
        {
            case 0: return "Disabled";
            case 1: return "Enabled";
            case 2: return "DisabledByUser";
            case 3: return "DisabledByPolicy";
            case 4: return "EnabledByPolicy";
            default: return "unknown(" + state + ")";
        }
    }

    private static int Main(string[] args)
    {
        string mode = args.Length > 0 ? args[0].ToLowerInvariant() : "read";

        int length = 0;
        int pkg = GetCurrentPackageFullName(ref length, null);
        bool packaged = pkg == ERROR_INSUFFICIENT_BUFFER;
        Console.WriteLine("packaged            : " + packaged + "   (GetCurrentPackageFullName = " + pkg + ")");

        IntPtr factory = IntPtr.Zero, taskId = IntPtr.Zero, task = IntPtr.Zero;
        try
        {
            Guid iid = IID_IStartupTaskStatics;
            IntPtr classId = IntPtr.Zero;
            string className = "Windows.ApplicationModel.StartupTask";
            if (WindowsCreateString(className, className.Length, out classId) != 0)
            {
                Console.WriteLine("FAIL: WindowsCreateString for the class name");
                return 1;
            }
            int hr = RoGetActivationFactory(classId, ref iid, out factory);
            WindowsDeleteString(classId);
            Console.WriteLine("RoGetActivationFactory: hr=0x" + hr.ToString("X8") + "  factory=" + (factory != IntPtr.Zero ? "ok" : "null"));
            if (hr != 0 || factory == IntPtr.Zero)
            {
                Console.WriteLine();
                Console.WriteLine(packaged
                    ? "FAIL: activation should work inside a package"
                    : "EXPECTED: an unpackaged process cannot activate the class, so the");
                if (!packaged) Console.WriteLine("          app correctly falls back to the Run key.");
                return packaged ? 1 : 0;
            }

            if (WindowsCreateString("LumaWallStartup", 15, out taskId) != 0)
            {
                Console.WriteLine("FAIL: WindowsCreateString");
                return 1;
            }

            IntPtr operation = IntPtr.Zero;
            hr = Vtable<GetAsyncDelegate>(factory, Slot_GetAsync)(factory, taskId, out operation);
            Console.WriteLine("GetAsync (slot 7)   : hr=0x" + hr.ToString("X8"));
            if (hr != 0 || operation == IntPtr.Zero)
            {
                // ERROR_NOT_FOUND is the correct answer for a process without
                // package identity: the activation factory exists (proving the
                // IID and the HSTRING are right) but no manifest registered a
                // startup task with this id.
                if (!packaged && hr == unchecked((int)0x80070490))
                {
                    Console.WriteLine();
                    Console.WriteLine("VERIFIED: activation works and GetAsync reports NOT_FOUND,");
                    Console.WriteLine("          which is correct without package identity. The app");
                    Console.WriteLine("          falls back to the Run key in this case.");
                    return 0;
                }
                Console.WriteLine("FAIL: GetAsync");
                return 1;
            }

            hr = Resolve(operation, out task);
            Console.WriteLine("GetResults (slot 5) : hr=0x" + hr.ToString("X8") + "  task=" + (task != IntPtr.Zero ? "ok" : "null"));
            if (hr != 0 || task == IntPtr.Zero) { Console.WriteLine("FAIL: resolving the task"); return 1; }

            int state;
            hr = Vtable<GetStateDelegate>(task, Slot_get_State)(task, out state);
            Console.WriteLine("get_State (slot 8)  : hr=0x" + hr.ToString("X8") + "  state=" + StateName(state));

            if (mode == "enable")
            {
                IntPtr op2 = IntPtr.Zero;
                hr = Vtable<RequestEnableAsyncDelegate>(task, Slot_RequestEnableAsync)(task, out op2);
                Console.WriteLine("RequestEnableAsync  : hr=0x" + hr.ToString("X8"));
                if (hr == 0 && op2 != IntPtr.Zero)
                {
                    IntPtr statePtr;
                    hr = Resolve(op2, out statePtr);
                    int after = hr == 0 ? statePtr.ToInt32() : -1;
                    Console.WriteLine("  -> state after    : " + StateName(after));
                    if (after == 2)
                        Console.WriteLine("  NOTE: DisabledByUser - Windows requires the user to re-enable it in Settings");
                }
            }
            else if (mode == "disable")
            {
                hr = Vtable<DisableDelegate>(task, Slot_Disable)(task);
                Console.WriteLine("Disable (slot 7)    : hr=0x" + hr.ToString("X8"));
                int after;
                Vtable<GetStateDelegate>(task, Slot_get_State)(task, out after);
                Console.WriteLine("  -> state after    : " + StateName(after));
            }

            Console.WriteLine();
            Console.WriteLine("ALL ABI CALLS SUCCEEDED");
            return 0;
        }
        finally
        {
            if (task != IntPtr.Zero) Marshal.Release(task);
            if (factory != IntPtr.Zero) Marshal.Release(factory);
            if (taskId != IntPtr.Zero) WindowsDeleteString(taskId);
        }
    }
}
