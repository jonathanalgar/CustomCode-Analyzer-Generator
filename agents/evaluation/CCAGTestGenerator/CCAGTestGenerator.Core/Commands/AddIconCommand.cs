using CCAGTestGenerator.Core.Services;

namespace CCAGTestGenerator.Core.Commands
{
    /// <summary>
    /// The command handler for <c>--addicon</c>, which adds an icon resource to the project
    /// (as an embedded resource) and updates the OSInterface attribute with the icon name.
    /// </summary>
    public static class AddIconCommand
    {
        /// <summary>
        /// Executes the addicon command, modifying the interface's [OSInterface] attribute
        /// to include <c>IconResourceName</c> and updating the project's <c>.csproj</c>.
        /// </summary>
        /// <param name="args">CLI arguments</param>
        public static async Task Execute(string[] args)
        {
            if (args.Length != 3)
            {
                Console.WriteLine(
                    "Usage: CCAGTestGenerator --addicon <source-file> <icon-filename>"
                );
                return;
            }

            string sourceFilePath = args[1];
            string iconFilename = args[2];

            string sourceCode = await File.ReadAllTextAsync(sourceFilePath);
            string updatedSourceCode = CodeModificationService.AddIconToInterface(
                sourceCode,
                iconFilename
            );
            await File.WriteAllTextAsync(sourceFilePath, updatedSourceCode);

            // Update the csproj file
            string sourceDir =
                Path.GetDirectoryName(Path.GetFullPath(sourceFilePath))
                ?? throw new InvalidOperationException("Source directory cannot be determined.");
            var projectFiles = Directory.GetFiles(sourceDir, "*.csproj");
            if (projectFiles.Length == 0)
                throw new InvalidOperationException("No .csproj file found in source directory");

            string csprojPath = projectFiles[0];
            string csprojContent = await File.ReadAllTextAsync(csprojPath);
            if (!csprojContent.Contains($"<EmbeddedResource Include=\"{iconFilename}\""))
            {
                string itemGroupContent =
                    $"\n  <ItemGroup>\n    <EmbeddedResource Include=\"{iconFilename}\" />\n  </ItemGroup>\n";
                if (csprojContent.Contains("</Project>"))
                {
                    csprojContent = csprojContent.Replace(
                        "</Project>",
                        $"{itemGroupContent}</Project>"
                    );
                }
                else
                {
                    csprojContent += itemGroupContent;
                }
                await File.WriteAllTextAsync(csprojPath, csprojContent);
                Console.WriteLine($"Added {iconFilename} as EmbeddedResource to project file");
            }

            Console.WriteLine(
                $"Successfully updated interface and project file with icon resource: {iconFilename}"
            );
        }
    }
}
