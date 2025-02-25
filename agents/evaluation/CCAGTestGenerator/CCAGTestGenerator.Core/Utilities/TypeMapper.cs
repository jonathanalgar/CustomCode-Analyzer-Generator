using System.Globalization;

namespace CCAGTestGenerator.Core.Utilities
{
    /// <summary>
    /// Provides functionality to map between various .NET data types and their
    /// string representations for use in test generation.
    /// </summary>
    public static class TypeMapper
    {
        /// <summary>
        /// Maintains a dictionary of known type mappings, with parsing and formatting delegates.
        /// Key is a string representing the type name (e.g. "string", "int", "byte[]").
        /// </summary>
        private static readonly IReadOnlyDictionary<
            string,
            (string NetType, Func<string, object> Parser, Func<object, string> Formatter)
        > TypeMappings = new Dictionary<
            string,
            (string, Func<string, object>, Func<object, string>)
        >(StringComparer.OrdinalIgnoreCase)
        {
            ["string"] = ("System.String", s => s, v => v is null ? "null" : $"\"{v}\""),
            ["int"] = (
                "System.Int32",
                s => int.Parse(s, CultureInfo.InvariantCulture),
                v => v?.ToString() ?? "0"
            ),
            ["Int32"] = (
                "System.Int32",
                s => int.Parse(s, CultureInfo.InvariantCulture),
                v => v?.ToString() ?? "0"
            ),
            ["long"] = (
                "System.Int64",
                s => long.Parse(s, CultureInfo.InvariantCulture),
                v => $"{v}L"
            ),
            ["float"] = (
                "System.Single",
                s => float.Parse(s, CultureInfo.InvariantCulture),
                v => $"{v}f"
            ),
            ["decimal"] = (
                "System.Decimal",
                s => decimal.Parse(s, CultureInfo.InvariantCulture),
                v => $"{v}m"
            ),
            ["double"] = (
                "System.Double",
                s => double.Parse(s, CultureInfo.InvariantCulture),
                v => $"{v}d"
            ),
            ["Double"] = (
                "System.Double",
                s => double.Parse(s, CultureInfo.InvariantCulture),
                v => $"{v}d"
            ),
            ["bool"] = (
                "System.Boolean",
                s => bool.Parse(s),
                v => v?.ToString()?.ToLowerInvariant() ?? "false"
            ),
            ["DateTime"] = (
                "System.DateTime",
                s => DateTime.Parse(s, CultureInfo.InvariantCulture),
                v =>
                    $"DateTime.Parse(\"{((DateTime)v).ToString("O")}\", CultureInfo.InvariantCulture)"
            ),
            ["byte[]"] = (
                "System.Byte[]",
                Convert.FromBase64String,
                v =>
                    v is null
                        ? "null"
                        : $"Convert.FromBase64String(\"{Convert.ToBase64String((byte[])v)}\")"
            ),
        };

        /// <summary>
        /// Attempts to retrieve parsing and formatting logic for a given type name.
        /// </summary>
        /// <param name="typeName">The type name, e.g. "int" or "string".</param>
        /// <param name="info">The mapping info (NetType, Parser, Formatter) if found.</param>
        /// <returns><c>true</c> if the type is known; otherwise <c>false</c>.</returns>
        public static bool TryGetTypeInfo(
            string typeName,
            out (string NetType, Func<string, object> Parser, Func<object, string> Formatter) info
        )
        {
            return TypeMappings.TryGetValue(typeName, out info);
        }

        /// <summary>
        /// Attempts to parse a string representation of a value into a .NET object,
        /// respecting the known type mappings defined above.
        /// </summary>
        /// <param name="value">The string to parse (may be null).</param>
        /// <param name="typeName">The name of the type to parse into.</param>
        /// <returns>An object of the requested type, or null if the type is reference type and the value is empty or 'null'.</returns>
        public static object? ParseValue(string? value, string typeName)
        {
            if (string.IsNullOrEmpty(value))
            {
                return IsReferenceType(typeName) ? null : ParseNonNull(value ?? "0", typeName);
            }
            if (
                value.Equals("null", StringComparison.OrdinalIgnoreCase)
                && IsReferenceType(typeName)
            )
                return null;
            if (
                typeName.Equals("byte[]", StringComparison.OrdinalIgnoreCase)
                && value.StartsWith("path:", StringComparison.OrdinalIgnoreCase)
            )
            {
                return value;
            }
            return ParseNonNull(value, typeName);
        }

        /// <summary>
        /// Internal helper that attempts to parse a non-null value.
        /// Throws if the type is unsupported or parsing fails.
        /// </summary>
        private static object ParseNonNull(string value, string typeName)
        {
            if (!TryGetTypeInfo(typeName, out var info))
                throw new ArgumentException($"Unsupported type: {typeName}");
            try
            {
                return info.Parser(value);
            }
            catch (Exception ex)
            {
                throw new FormatException($"Could not parse '{value}' as {typeName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Formats a given object for insertion into generated test code, e.g. quoting strings or
        /// handling numeric suffixes. For byte arrays referencing paths, transforms them into a
        /// <c>File.ReadAllBytes(...)</c> call.
        /// </summary>
        /// <param name="value">The object to format into a code expression.</param>
        /// <param name="typeName">The type name for which to format.</param>
        /// <returns>A string that can be used directly in a generated test method argument list.</returns>
        public static string FormatValueForTest(object? value, string typeName)
        {
            const string prefix = "path:";
            if (
                typeName.Equals("byte[]", StringComparison.OrdinalIgnoreCase)
                && value is string s
                && s.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)
            )
            {
                string relativePath = s.Substring(prefix.Length).Trim();
                string fileName = Path.GetFileName(relativePath);
                return $"File.ReadAllBytes(@\"TestResources\\{fileName}\")";
            }
            if (value == null && IsReferenceType(typeName))
                return "null";
            if (!TryGetTypeInfo(typeName, out var info))
                return value?.ToString() ?? "null";
            try
            {
                return info.Formatter(value ?? throw new ArgumentNullException(nameof(value)));
            }
            catch (Exception ex)
            {
                throw new FormatException($"Could not format value for {typeName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Determines whether a type name should be considered a reference type for the
        /// purpose of allowing null assignment.
        /// </summary>
        /// <param name="typeName">The type name (e.g. "string", "byte[]").</param>
        /// <returns>True if the type is considered a reference type; otherwise false.</returns>
        private static bool IsReferenceType(string typeName)
        {
            var lower = typeName.ToLowerInvariant();
            return lower == "string" || lower == "byte[]";
        }
    }
}
