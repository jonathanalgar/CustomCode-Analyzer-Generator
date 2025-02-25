using CCAGTestGenerator.Core.Generators;
using CCAGTestGenerator.Core.Parsers;
using CCAGTestGenerator.Core.Services;
using CCAGTestGenerator.Core.Utilities;

namespace CCAGTestGenerator.Core.Commands
{
    /// <summary>
    /// Represents the command that generates test files based on a source file
    /// and a corresponding YAML test case specification.
    /// </summary>
    public static class GenerateTestsCommand
    {
        /// <summary>
        /// Main execution logic for generating XUnit test code from the given source
        /// and YAML. Optionally processes --paramMap for user-defined parameter mappings.
        /// </summary>
        /// <param name="args">CLI arguments</param>
        public static async Task Execute(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine(
                    "Usage: CCAGTestGenerator <source-file> <test-cases-yaml> [--paramMap <mapping-string>]"
                );
                return;
            }

            // Process optional parameter map
            Dictionary<(string YamlActionName, string YamlParamName), string> paramMap;
            Dictionary<string, string> actionMap;
            int mapFlagIndex = Array.IndexOf(args, "--paramMap");
            if (mapFlagIndex >= 0 && mapFlagIndex + 1 < args.Length)
            {
                string mapArg = args[mapFlagIndex + 1];
                (paramMap, actionMap) = ParamMapParser.ParseParamMap(mapArg);
            }
            else
            {
                paramMap = new Dictionary<(string, string), string>(
                    new ParamMapParser.ActionYamlComparer()
                );
                actionMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            }

            string sourceFilePath = args[0];
            string yamlFilePath = args[1];

            string sourceCode = await File.ReadAllTextAsync(sourceFilePath);
            string yamlContent = await File.ReadAllTextAsync(yamlFilePath);

            // Determine output paths
            string implDir = Path.GetDirectoryName(sourceFilePath) ?? "";
            string solutionDir = Directory.GetParent(implDir)?.FullName ?? "";
            string gtTestDir = Path.Combine(solutionDir, "GroundTruthTests");
            Directory.CreateDirectory(gtTestDir);

            string outputFileName = Path.GetFileNameWithoutExtension(sourceFilePath) + "Tests.cs";
            string outputPath = Path.Combine(gtTestDir, outputFileName);

            // Prepare TestResources folder
            string testResourcesFolder = Path.Combine(gtTestDir, "TestResources");
            Directory.CreateDirectory(testResourcesFolder);

            // Copy binary resources referenced in the YAML
            FileResourceService.CopyTestResources(yamlContent, yamlFilePath, testResourcesFolder);

            // If resources were copied, update the csproj
            if (FileResourceService.HasCopiedResources(testResourcesFolder))
            {
                string csprojPath = Path.Combine(gtTestDir, "GroundTruthTests.csproj");
                FileResourceService.UpdateCsprojForTestResources(csprojPath);
            }
            else
            {
                Console.WriteLine("No resources found in TestResources. Skipping csproj update.");
            }

            // Parse library info from the source file
            var libInfo = LibraryParser.ParseLibrary(sourceCode);

            // Possibly remap the action name if the user requested a rename
            string actionNameToUse = libInfo.MethodName;
            if (
                actionMap.TryGetValue(libInfo.MethodName, out string? mappedAction)
                && mappedAction is not null
            )
            {
                actionNameToUse = mappedAction;
            }

            // Parse test cases from YAML
            var testCases = TestCaseParser.ParseYaml(
                yamlContent,
                actionNameToUse,
                libInfo.Parameters,
                libInfo.ReturnType,
                paramMap
            );

            // Generate the XUnit test code
            string testCode = XUnitTestGenerator.GenerateTests(libInfo, testCases);

            // Write the test code to the output file
            await File.WriteAllTextAsync(outputPath, testCode);
            Console.WriteLine($"Successfully generated test file: {outputPath}");
            Console.WriteLine($"Processed {testCases.Count} test cases");
        }
    }
}
