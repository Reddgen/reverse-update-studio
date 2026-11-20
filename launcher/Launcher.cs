using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher
{
    [STAThread]
    private static void Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string launch = Path.Combine(dir, "Launch.cmd");

        if (!File.Exists(launch))
        {
            MessageBox.Show(
                "Launch.cmd was not found next to this launcher.\r\n\r\n" +
                "Extract the complete package and run Setup.cmd.",
                "Reverse Update Studio",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        try
        {
            var start = new ProcessStartInfo
            {
                FileName = Path.Combine(Environment.SystemDirectory, "cmd.exe"),
                Arguments = "/c \"" + launch + "\"",
                WorkingDirectory = dir,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(start);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Could not start Reverse Update Studio.\r\n\r\n" + ex.Message,
                "Reverse Update Studio",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }
}
