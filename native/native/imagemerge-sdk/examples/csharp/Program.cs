using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

internal static class Program
{
    static Program()
    {
        NativeLibrary.SetDllImportResolver(typeof(Program).Assembly,
            (name, assembly, searchPath) =>
                name == "imagemerge.dll"
                    ? NativeLibrary.Load(Path.Combine(AppContext.BaseDirectory, "lib", name))
                    : IntPtr.Zero);
    }

    [DllImport("imagemerge.dll", CallingConvention = CallingConvention.Cdecl,
        EntryPoint = "imagemerge_sdk_run")]
    private static extern IntPtr Run(IntPtr executablePathUtf8, IntPtr requestJsonUtf8);

    [DllImport("imagemerge.dll", CallingConvention = CallingConvention.Cdecl,
        EntryPoint = "imagemerge_sdk_free_string")]
    private static extern void FreeString(IntPtr value);

    private static void Main()
    {
        string executable = @"runtime\ImageMerge\ImageMerge.exe";
        string request =
            "{\"inputs\":[{\"path\":\"C:\\\\media\\\\trip\",\"prefix\":\"trip\"}],"
            + "\"output\":\"C:\\\\media\\\\merged\",\"mode\":\"copy_keep\"}";

        IntPtr executablePointer = Marshal.StringToCoTaskMemUTF8(executable);
        IntPtr requestPointer = Marshal.StringToCoTaskMemUTF8(request);
        try
        {
            IntPtr resultPointer = Run(executablePointer, requestPointer);
            if (resultPointer == IntPtr.Zero)
            {
                throw new InvalidOperationException("ImageMerge SDK returned no result.");
            }

            try
            {
                Console.WriteLine(Marshal.PtrToStringUTF8(resultPointer));
            }
            finally
            {
                FreeString(resultPointer);
            }
        }
        finally
        {
            Marshal.FreeCoTaskMem(executablePointer);
            Marshal.FreeCoTaskMem(requestPointer);
        }
    }
}
