namespace CCAGTestGenerator.Core.Utilities
{
    public static class ParamMapParser
    {
        public static (
            Dictionary<(string YamlActionName, string YamlParamName), string> ParamMap,
            Dictionary<string, string> ActionMap
        ) ParseParamMap(string mapString)
        {
            var trimmed = mapString.Trim();
            if (
                trimmed.StartsWith('(')
                && trimmed.EndsWith(')')
                && trimmed.Count(c => c == '(') == 1
                && trimmed.Count(c => c == ')') == 1
            )
            {
                trimmed = trimmed[1..^1];
            }

            var segments = trimmed.Split(["),("], StringSplitOptions.RemoveEmptyEntries);
            var paramMap = new Dictionary<(string YamlActionName, string YamlParamName), string>(
                new ActionYamlComparer()
            );
            var actionMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            foreach (var rawSegment in segments)
            {
                var segment = rawSegment.Trim('(', ')').Trim();
                int eqIndex = segment.IndexOf('=');
                if (eqIndex < 0)
                {
                    Console.WriteLine($"Skipping invalid mapping segment: '{segment}' (no '=')");
                    continue;
                }

                var leftPart = segment.Substring(0, eqIndex).Trim();
                var rightPart = segment.Substring(eqIndex + 1).Trim();

                bool leftHasColon = leftPart.Contains(':');
                bool rightHasColon = rightPart.Contains(':');

                if (!leftHasColon && !rightHasColon)
                {
                    // e.g. "Power=RaiseToPower"
                    var yamlAction = leftPart;
                    var csharpMethod = rightPart;
                    actionMap[csharpMethod] = yamlAction;
                }
                else if (leftHasColon && rightHasColon)
                {
                    // e.g. "Power:base=RaiseToPower:baseNumber"
                    var (yamlAction, yamlParam) = SplitOnColon(leftPart);
                    var (csharpMethod, csharpParam) = SplitOnColon(rightPart);
                    paramMap[(yamlAction, yamlParam)] = csharpParam;
                    if (!actionMap.ContainsKey(csharpMethod))
                        actionMap[csharpMethod] = yamlAction;
                }
                else
                {
                    Console.WriteLine(
                        $"Skipping partially-specified paramMap segment: '{segment}'"
                    );
                }
            }

            return (paramMap, actionMap);

            static (string, string) SplitOnColon(string s)
            {
                var idx = s.IndexOf(':');
                if (idx < 0)
                    return (s, "");
                var left = s[..idx].Trim();
                var right = s[(idx + 1)..].Trim();
                return (left, right);
            }
        }

        public sealed class ActionYamlComparer
            : IEqualityComparer<(string YamlActionName, string YamlParamName)>
        {
            public bool Equals(
                (string YamlActionName, string YamlParamName) x,
                (string YamlActionName, string YamlParamName) y
            )
            {
                return x.YamlActionName.Equals(y.YamlActionName, StringComparison.OrdinalIgnoreCase)
                    && x.YamlParamName.Equals(y.YamlParamName, StringComparison.OrdinalIgnoreCase);
            }

            public int GetHashCode((string YamlActionName, string YamlParamName) obj)
            {
                unchecked
                {
                    return (obj.YamlActionName.ToLowerInvariant().GetHashCode() * 397)
                        ^ obj.YamlParamName.ToLowerInvariant().GetHashCode();
                }
            }
        }
    }
}
