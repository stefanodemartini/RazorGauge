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
    /// <summary>
    /// Empirical correction applied by "Ø ±" to a profile hand-traced over a scan: the current
    /// gauge reads the line thinner than it is. Negative decreases. Temporary, until the laser
    /// reader replaces it.
    /// </summary>
    public double ScanInflatePercent { get; set; } = 8.0;

    /// <summary>Fixed amount added to every diameter in "mm" mode. 0.06 = the near-constant gap
    /// measured on the Phantom Hover (2026-10-21).</summary>
    public double ScanOffsetMm { get; set; } = 0.06;

    /// <summary>"mm" (fixed offset, default) or "%" (proportional).</summary>
    public string ScanCorrectionUnit { get; set; } = "mm";
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
