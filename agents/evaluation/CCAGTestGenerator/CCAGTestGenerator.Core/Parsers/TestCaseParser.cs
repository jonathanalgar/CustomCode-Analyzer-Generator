using CCAGTestGenerator.Core.Models;
using CCAGTestGenerator.Core.Utilities;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace CCAGTestGenerator.Core.Parsers
{
    public static class TestCaseParser
    {
        /// <summary>
        /// Reads YAML content describing the test cases, locates the relevant action block by name,
        /// and converts test-cases into (<c>inputs[], output</c>) pairs. Optionally uses <c>paramMap</c>
        /// to match YAML parameter names to C# parameter names if they differ.
        /// </summary>
        /// <param name="yamlContent">The entire YAML test specification.</param>
        /// <param name="actionMethodName">The method name in the interface which we want test data for.</param>
        /// <param name="csharpParameters">A list of (paramName, paramType) from the method signature.</param>
        /// <param name="csharpReturnType">The return type of the method in C# (for parsing expected output).</param>
        /// <param name="paramMap">
        /// An optional dictionary mapping (YamlActionName, YamlParamName) -> C#ParamName, and
        /// (YamlActionName) -> methodName if there's an action rename.
        /// </param>
        /// <returns>A list of test-case objects, each containing input array and expected output.</returns>
        /// <exception cref="InvalidOperationException">If action or parameter names cannot be matched.</exception>
        public static List<(object[] inputs, object? output)> ParseYaml(
            string yamlContent,
            string actionMethodName,
            IReadOnlyList<(string ParamName, string ParamType)> csharpParameters,
            string csharpReturnType,
            Dictionary<(string YamlActionName, string YamlParamName), string>? paramMap = null
        )
        {
            var deserializer = new DeserializerBuilder()
                .WithNamingConvention(CamelCaseNamingConvention.Instance)
                .Build();
            var spec =
                deserializer.Deserialize<YamlSpec>(yamlContent)
                ?? new YamlSpec { Description = string.Empty, Actions = [] };
            var actions = spec.Actions ?? [];

            bool singleActionInYaml = actions.Count == 1 && csharpParameters.Count == 1;
            KeyValuePair<string, YamlAction> actionKvp;
            if (singleActionInYaml)
            {
                actionKvp = actions.First();
            }
            else
            {
                actionKvp = actions.FirstOrDefault(a =>
                    a.Key.Equals(actionMethodName, StringComparison.OrdinalIgnoreCase)
                );
                if (string.IsNullOrEmpty(actionKvp.Key))
                    throw new InvalidOperationException(
                        $"Action '{actionMethodName}' not found in YAML."
                    );
            }

            var yamlAction = actionKvp.Value;
            if (yamlAction.Params == null || yamlAction.TestCases == null)
                throw new InvalidOperationException(
                    $"Action '{actionKvp.Key}' missing 'Params' or 'TestCases' in YAML."
                );

            bool singleParamFallback = csharpParameters.Count == 1;
            if (!singleActionInYaml && yamlAction.Params.Count != csharpParameters.Count)
                throw new InvalidOperationException(
                    $"Mismatch in parameter count: YAML has {yamlAction.Params.Count}, C# method has {csharpParameters.Count}."
                );

            var testCases = new List<(object[] inputs, object? output)>();
            foreach (var tc in yamlAction.TestCases)
            {
                var inputsDict = tc.Inputs ?? [];
                var inputValues = new object[csharpParameters.Count];
                for (int i = 0; i < yamlAction.Params.Count; i++)
                {
                    string yamlParamName = yamlAction.Params[i];
                    string csharpParamName;
                    if (singleParamFallback)
                    {
                        csharpParamName = csharpParameters[0].ParamName;
                    }
                    else
                    {
                        paramMap ??= new Dictionary<(string, string), string>(
                            new ParamMapParser.ActionYamlComparer()
                        );
                        if (
                            !paramMap.TryGetValue(
                                (actionKvp.Key, yamlParamName),
                                out string? mappedCsharpParamName
                            ) || string.IsNullOrEmpty(mappedCsharpParamName)
                        )
                        {
                            throw new InvalidOperationException(
                                $"No mapping found for action '{actionKvp.Key}', YAML param '{yamlParamName}'. Provide --paramMap with all required mappings."
                            );
                        }
                        csharpParamName = mappedCsharpParamName;
                    }

                    int paramIndex = csharpParameters
                        .Select((p, idx) => (p, idx))
                        .FirstOrDefault(x =>
                            x.p.ParamName.Equals(csharpParamName, StringComparison.Ordinal)
                        )
                        .idx;

                    if (paramIndex < 0)
                        throw new InvalidOperationException(
                            $"No parameter in C# named '{csharpParamName}' for method '{actionMethodName}'."
                        );

                    if (
                        !inputsDict.TryGetValue(yamlParamName, out object? rawObj)
                        || rawObj == null
                    )
                        throw new InvalidOperationException(
                            $"Test case missing required YAML param '{yamlParamName}'."
                        );

                    string? rawStr = rawObj?.ToString();
                    var paramType = csharpParameters[paramIndex].ParamType;
                    var parsedValue = TypeMapper.ParseValue(rawStr, paramType);
                    inputValues[paramIndex] = parsedValue!;
                }

                var outputValue = TypeMapper.ParseValue(tc.Expected?.ToString(), csharpReturnType);
                testCases.Add((inputValues, outputValue));
            }

            return testCases;
        }

        /// <summary>
        /// Parses the YAML to get the action name and list of parameter names from the first action found.
        /// Useful in <c>--report</c> mode to simply display the data without generating test code.
        /// </summary>
        /// <param name="yamlContent">The entire YAML content describing possible actions.</param>
        /// <returns>A tuple containing the action name and a list of parameter names.</returns>
        public static (string ActionName, List<string> ParamNames) ParseYamlActionParams(
            string yamlContent
        )
        {
            var deserializer = new DeserializerBuilder()
                .WithNamingConvention(CamelCaseNamingConvention.Instance)
                .Build();
            var spec =
                deserializer.Deserialize<YamlSpec>(yamlContent)
                ?? new YamlSpec { Description = string.Empty, Actions = [] };
            if (spec.Actions == null || spec.Actions.Count == 0)
                throw new InvalidOperationException("No actions found in YAML.");

            var first = spec.Actions.First();
            var actionName = first.Key;
            var actionData = first.Value;
            actionData.Params ??= [];
            return (actionName, actionData.Params);
        }
    }
}
