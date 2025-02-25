using System.Xml.Linq;
using CCAGTestGenerator.Core.Models;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace CCAGTestGenerator.Core.Services
{
    public static class FileResourceService
    {
        private const string BinaryPathPrefix = "path:";

        /// <summary>
        /// Copies a single file from a local path reference prefixed by "path:" into the specified destination.
        /// Logs a warning instead of throwing an exception if the file does not exist.
        /// </summary>
        /// <param name="yamlValue">A string that starts with "path:" indicating the file to copy.</param>
        /// <param name="yamlFilePath">Path to the YAML file for resolving relative paths.</param>
        /// <param name="destinationFolder">The folder to which the file is copied.</param>
        public static void CopyBinaryResource(
            string yamlValue,
            string yamlFilePath,
            string destinationFolder
        )
        {
            if (yamlValue.StartsWith(BinaryPathPrefix, StringComparison.OrdinalIgnoreCase))
            {
                string relativePath = yamlValue.Substring(BinaryPathPrefix.Length).Trim();
                string yamlDirectory = Path.GetDirectoryName(yamlFilePath) ?? "";
                string sourcePath = Path.Combine(yamlDirectory, relativePath);

                if (!File.Exists(sourcePath))
                {
                    Console.WriteLine($"Warning: Binary file not found at {sourcePath}");
                    return;
                }

                Directory.CreateDirectory(destinationFolder);
                string fileName = Path.GetFileName(sourcePath);
                string destPath = Path.Combine(destinationFolder, fileName);
                File.Copy(sourcePath, destPath, overwrite: true);
                Console.WriteLine($"Copied binary resource: {sourcePath} -> {destPath}");
            }
        }

        /// <summary>
        /// Finds references to local files (prefixed by "path:") in the YAML test specification
        /// and copies those files into the specified <c>TestResources</c> folder.
        /// </summary>
        /// <param name="yamlContent">YAML content describing test actions and cases.</param>
        /// <param name="yamlFilePath">Path to the YAML file for relative path resolution.</param>
        /// <param name="destinationFolder">Folder to which any found resources are copied.</param>
        public static void CopyTestResources(
            string yamlContent,
            string yamlFilePath,
            string destinationFolder
        )
        {
            var deserializer = new DeserializerBuilder()
                .WithNamingConvention(CamelCaseNamingConvention.Instance)
                .Build();

            var spec = deserializer.Deserialize<YamlSpec>(yamlContent);

            if (spec?.Actions == null)
                return;

            var allTestCases = spec
                .Actions.Where(a => a.Value?.TestCases != null)
                .SelectMany(a => a.Value.TestCases);

            foreach (var testCase in allTestCases)
            {
                CopyResourcesFromInputs(testCase.Inputs, yamlFilePath, destinationFolder);

                if (
                    testCase.Expected is string expectedStr
                    && expectedStr.StartsWith(BinaryPathPrefix, StringComparison.OrdinalIgnoreCase)
                )
                {
                    CopyBinaryResource(expectedStr, yamlFilePath, destinationFolder);
                }
            }
        }

        /// <summary>
        /// Searches a test case's input dictionary for any "path:" references
        /// and copies those files via <see cref="CopyBinaryResource"/>.
        /// </summary>
        /// <param name="inputs">Key-value pairs that may include file references.</param>
        /// <param name="yamlFilePath">Path to the YAML file for relative path resolution.</param>
        /// <param name="destinationFolder">Folder where any located files are copied.</param>
        private static void CopyResourcesFromInputs(
            Dictionary<string, object>? inputs,
            string yamlFilePath,
            string destinationFolder
        )
        {
            if (inputs == null)
                return;

            foreach (
                var inputValue in inputs
                    .Values.OfType<string>()
                    .Where(value =>
                        value.StartsWith(BinaryPathPrefix, StringComparison.OrdinalIgnoreCase)
                    )
            )
            {
                CopyBinaryResource(inputValue, yamlFilePath, destinationFolder);
            }
        }

        /// <summary>
        /// Checks whether the specified <c>TestResources</c> folder contains at least one file.
        /// </summary>
        /// <param name="testResourcesFolderPath">Path to the test resources folder.</param>
        /// <returns>True if the folder has at least one file; otherwise false.</returns>
        public static bool HasCopiedResources(string testResourcesFolderPath)
        {
            return Directory.Exists(testResourcesFolderPath)
                && Directory
                    .EnumerateFiles(testResourcesFolderPath, "*", SearchOption.AllDirectories)
                    .Any();
        }

        /// <summary>
        /// Updates a .csproj file to include all files under <c>TestResources\**\*</c>
        /// as Content that is copied to the output directory.
        /// </summary>
        /// <param name="csprojPath">Path to the .csproj that will be modified.</param>
        public static void UpdateCsprojForTestResources(string csprojPath)
        {
            if (!File.Exists(csprojPath))
            {
                Console.WriteLine($"Error: CSProj file '{csprojPath}' not found.");
                return;
            }

            XDocument doc = XDocument.Load(csprojPath);
            if (doc.Root == null)
            {
                Console.WriteLine($"Error: Invalid csproj file '{csprojPath}'.");
                return;
            }
            XNamespace ns = doc.Root.GetDefaultNamespace();

            var itemGroup = new XElement(
                ns + "ItemGroup",
                new XElement(
                    ns + "Content",
                    new XAttribute("Include", @"TestResources\**\*"),
                    new XElement(ns + "CopyToOutputDirectory", "PreserveNewest")
                )
            );

            doc.Root.Add(itemGroup);
            doc.Save(csprojPath);
            Console.WriteLine($"Updated '{csprojPath}' to include TestResources as content.");
        }
    }
}
