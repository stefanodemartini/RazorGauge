namespace DiametroLineaDesktop.Models;
public class AppSettings
{
    public BackendSettings Backend { get; set; } = new();
    public ChartSettings Chart { get; set; } = new();
    public PrototypeSettings Prototype { get; set; } = new();
    public DesignSettings Design { get; set; } = new();
}
public class DesignSettings
{
    /// <summary>Language of the exported design sheet: "en", "zh" or "en+zh" (SheetText.Parse).</summary>
    public string PdfLanguage { get; set; } = "en";

    /// <summary>Nozzles (= real materials) a Compensate pass may use, 2–4. Last choice remembered.</summary>
    public int CompNozzleCount { get; set; } = 4;
}
public class PrototypeSettings
{
    /// <summary>Folder scanned (recursively) for piece .flp files. Empty = the default projects folder.</summary>
    public string LibraryFolder { get; set; } = string.Empty;
}
public class BackendSettings
{
    public string ProfileName { get; set; } = "ESP32 Lab";
    public string Host { get; set; } = "192.168.1.50";
    public int WebSocketPort { get; set; } = 81;
    public int HttpPort { get; set; } = 80;
    public bool AutoConnect { get; set; } = true;
    public int ReconnectSeconds { get; set; } = 3;
    public int ConnectTimeoutSeconds { get; set; } = 5;
    public bool LoadParamsOnConnect { get; set; } = true;
    public bool LoadMotorStatusOnConnect { get; set; } = true;
}
public class ChartSettings
{
    public bool ShowFilteredSeries { get; set; } = true;
    public bool ShowRawSeries { get; set; } = false;
    public bool AutoFit { get; set; } = true;
    public string Theme { get; set; } = "Light";
    public string XAxisUnit { get; set; } = "cm";
    public double SmoothingAlpha { get; set; } = 0.10;
    public int LineWidth { get; set; } = 2;
    public double FilteredOpacity { get; set; } = 1.0;
    public double RawOpacity { get; set; } = 0.65;
}
public class MeasurementPoint
{
    public double X { get; set; }
    public double RawY { get; set; }
    public double FilteredY { get; set; }
}
