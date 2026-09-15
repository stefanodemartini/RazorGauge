namespace FlyLinePhysics.Physics;

/// <summary>
/// Π(s), the momentum-to-drag ratio, and C(s), the continuity index derived from it — the two
/// metrics used to flag where a taper is likely to overshoot/undershoot during loop formation.
/// </summary>
public static class StabilityMetrics
{
    private const double DragEpsilon = 1e-12;

    /// <summary>
    /// Π(s) = m(s)·a / F_n,drag(s,v). Degenerates to +∞ where F_n,drag ≈ 0 (v≈0, no normal
    /// velocity component) instead of throwing — callers should check <see cref="IsDegenerate"/>.
    /// </summary>
    public static double MomentumToDragRatio(double linearMassKgM, double accelerationMs2, double normalDragNPerM)
    {
        if (Math.Abs(normalDragNPerM) < DragEpsilon)
            return double.PositiveInfinity;
        return linearMassKgM * accelerationMs2 / normalDragNPerM;
    }

    /// <summary>True for a Π (or any derived) value that carries no usable information.</summary>
    public static bool IsDegenerate(double value) => double.IsInfinity(value) || double.IsNaN(value);

    /// <summary>
    /// C(s) = |ΔΠ/Δs| / Π(s) at every point of <paramref name="pi"/>, using a central difference
    /// for interior points and a one-sided difference at the two ends. Wherever <paramref name="pi"/>
    /// itself is degenerate (see <see cref="IsDegenerate"/>), or its neighbour is, the result is
    /// <see cref="double.NaN"/> rather than a misleading finite number from IEEE arithmetic with an
    /// infinity in play.
    /// </summary>
    public static double[] ContinuityIndex(IReadOnlyList<double> xsCm, IReadOnlyList<double> pi)
    {
        if (xsCm.Count != pi.Count)
            throw new ArgumentException("xsCm and pi must have the same length.");

        int n = pi.Count;
        var c = new double[n];
        for (int i = 0; i < n; i++)
        {
            int lo = i == 0 ? 0 : i - 1;
            int hi = i == n - 1 ? n - 1 : i + 1;
            if (lo == hi || IsDegenerate(pi[i]) || IsDegenerate(pi[lo]) || IsDegenerate(pi[hi]))
            {
                c[i] = double.NaN;
                continue;
            }
            double dPi = pi[hi] - pi[lo];
            double dsCm = xsCm[hi] - xsCm[lo];
            double slope = dPi / dsCm;
            c[i] = Math.Abs(pi[i]) < DragEpsilon ? double.NaN : Math.Abs(slope) / Math.Abs(pi[i]);
        }
        return c;
    }
}
