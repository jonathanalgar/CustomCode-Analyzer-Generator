using System.Text;
using CCAGTestGenerator.Core.Parsers;
using CCAGTestGenerator.Core.Utilities;

namespace CCAGTestGenerator.Core.Generators
{
    public static class XUnitTestGenerator
    {
        /// Creates an XUnit test class source code, including a constructor to instantiate the library,
        /// a static <c>TestData</c> property for parameterized test inputs, and one test method
        /// that verifies the result matches the expected output.
        /// </summary>
        /// <param name="info">Parsed library info (namespace, class name, etc.).</param>
        /// <param name="testCases">A list of test case tuples (input array, expected output).</param>
        /// <returns>The complete test class as a string.</returns>

        /// </summary>
        public static string GenerateTests(
            ExternalLibraryInfo info,
            IReadOnlyList<(object[] inputs, object? output)> testCases
        )
        {
            // Determine if we should generate a PNG validation test.
            bool usePngValidation = false;
            if (
                info.ReturnType != null
                && info.ReturnType.Equals("byte[]", StringComparison.OrdinalIgnoreCase)
                && testCases.Count > 0
                && testCases[0].output is string outStr
                && outStr.StartsWith("path:", StringComparison.OrdinalIgnoreCase)
            )
            {
                string relativePath = outStr.Substring("path:".Length).Trim();
                if (
                    Path.GetExtension(relativePath)
                        .Equals(".png", StringComparison.OrdinalIgnoreCase)
                )
                {
                    usePngValidation = true;
                }
            }

            var sb = new StringBuilder();
            sb.AppendLine("using Xunit;");
            sb.AppendLine("using System;");
            sb.AppendLine("using System.Collections.Generic;");
            sb.AppendLine("using System.IO;");
            sb.AppendLine();
            sb.AppendLine($"namespace {info.Namespace}.Tests");
            sb.AppendLine("{");
            sb.AppendLine($"    public class {info.ClassName}Tests");
            sb.AppendLine("    {");
            sb.AppendLine($"        private readonly {info.ClassName} _library;");
            sb.AppendLine();
            sb.AppendLine($"        public {info.ClassName}Tests()");
            sb.AppendLine("        {");
            sb.AppendLine($"            _library = new {info.ClassName}();");
            sb.AppendLine("        }");
            sb.AppendLine();
            sb.AppendLine(
                "        public static IEnumerable<object[]> TestData => new List<object[]>"
            );
            sb.AppendLine("        {");

            foreach (var (inputs, output) in testCases)
            {
                sb.Append("            new object[] { ");
                for (int i = 0; i < info.Parameters.Count; i++)
                {
                    var (_, paramType) = info.Parameters[i];
                    string formattedValue;
                    if (
                        paramType.Equals("byte[]", StringComparison.OrdinalIgnoreCase)
                        && inputs[i] is string s
                        && s.StartsWith("path:", StringComparison.OrdinalIgnoreCase)
                    )
                    {
                        string relativePath = s["path:".Length..].Trim();
                        string fileName = Path.GetFileName(relativePath);
                        formattedValue = $"File.ReadAllBytes(@\"TestResources/{fileName}\")";
                    }
                    else
                    {
                        formattedValue = TypeMapper.FormatValueForTest(inputs[i], paramType);
                    }
                    sb.Append(formattedValue);
                    if (i < info.Parameters.Count - 1)
                    {
                        sb.Append(", ");
                    }
                }
                if (!usePngValidation)
                {
                    sb.Append(", ");
                    if (
                        info.ReturnType != null
                        && info.ReturnType.Equals("byte[]", StringComparison.OrdinalIgnoreCase)
                        && output is string outStr2
                        && outStr2.StartsWith("path:", StringComparison.OrdinalIgnoreCase)
                    )
                    {
                        string relativePath = outStr2.Substring("path:".Length).Trim();
                        string fileName = Path.GetFileName(relativePath);
                        sb.Append($"File.ReadAllBytes(@\"TestResources/{fileName}\")");
                    }
                    else
                    {
                        sb.Append(
                            TypeMapper.FormatValueForTest(output, info.ReturnType ?? string.Empty)
                        );
                    }
                }
                sb.AppendLine(" },");
            }
            sb.AppendLine("        };");
            sb.AppendLine();

            var methodParams = info.Parameters.Select(p => $"{p.ParamType} {p.ParamName}").ToList();
            string methodNameSuffix = "";
            if (!usePngValidation && info.ReturnType != null)
            {
                methodParams.Add($"{info.ReturnType} expectedOutput");
                methodNameSuffix = "_ValidInput_ReturnsExpectedOutput";
            }
            else if (usePngValidation)
            {
                methodNameSuffix = "_ValidInput_ReturnsValidPng";
            }
            var methodSignature =
                $"public void {info.MethodName}{methodNameSuffix}({string.Join(", ", methodParams)})";
            sb.AppendLine("        [Theory]");
            sb.AppendLine("        [MemberData(nameof(TestData))]");
            sb.AppendLine($"        {methodSignature}");
            sb.AppendLine("        {");
            sb.AppendLine("            // Act");
            var callArgs = string.Join(", ", info.Parameters.Select(p => p.ParamName));
            sb.AppendLine($"            var result = _library.{info.MethodName}({callArgs});");
            sb.AppendLine();
            sb.AppendLine("            // Assert");
            if (usePngValidation)
            {
                sb.AppendLine(
                    "            // Validate that result is a valid PNG file by checking the PNG signature."
                );
                sb.AppendLine(
                    "            byte[] pngSignature = new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 };"
                );
                sb.AppendLine(
                    "            Assert.True(result != null && result.Length >= pngSignature.Length, \"Output is not a valid PNG file.\");"
                );
                sb.AppendLine("            for (int i = 0; i < pngSignature.Length; i++)");
                sb.AppendLine("            {");
                sb.AppendLine("                Assert.Equal(pngSignature[i], result[i]);");
                sb.AppendLine("            }");
            }
            else
            {
                sb.AppendLine("            Assert.Equal(expectedOutput, result);");
            }
            sb.AppendLine("        }");
            sb.AppendLine("    }");
            sb.AppendLine("}");
            return sb.ToString().TrimEnd();
        }
    }
}
