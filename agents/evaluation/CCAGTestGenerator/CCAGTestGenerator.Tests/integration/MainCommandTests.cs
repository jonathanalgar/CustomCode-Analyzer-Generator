using CCAGTestGenerator.Core;
using Xunit;

namespace CCAGTestGenerator.Tests.integration
{
    /// <summary>
    /// Contains integration tests for the main command entry point of the CCAGTestGenerator application.
    /// </summary>

    public class MainCommandTests
    {
        /// <summary>
        /// Creates a unique temporary directory on the file system for testing,
        /// ensuring an isolated environment for file generation and cleanup.
        /// </summary>
        /// <returns>The full path to the newly created temporary directory.</returns>
        private static string CreateTemporaryDirectory()
        {
            string tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
            Directory.CreateDirectory(tempDir);
            return tempDir;
        }

        /// <summary>
        /// Captures standard console output for a given asynchronous action.
        /// </summary>
        /// <param name="action">A function that produces console output when awaited.</param>
        /// <returns>A task representing the asynchronous operation, containing the captured console output.</returns>
        private static async Task<string> CaptureConsoleOutput(Func<Task> action)
        {
            var originalOut = Console.Out;
            using var sw = new StringWriter();
            Console.SetOut(sw);
            await action();
            await Console.Out.FlushAsync();
            Console.SetOut(originalOut);
            return sw.ToString();
        }

        [Fact]
        public async Task ShouldGenerateExpectedTestFile_WhenValidSourceAndYamlProvided()
        {
            // Arrange
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string sourceFileName = "HashingLibrary.cs";
                string sourceFilePath = Path.Combine(projectDir, sourceFileName);
                string sourceCode = HashingTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string yamlFileName = "sha1.yaml";
                string yamlFilePath = Path.Combine(tempDir, yamlFileName);
                string yamlContent = HashingTestConstants.YamlContent;
                await File.WriteAllTextAsync(yamlFilePath, yamlContent);

                string[] args = [sourceFilePath, yamlFilePath];

                // Act
                await Program.Main(args);

                // Assert
                string groundTruthTestsDir = Path.Combine(tempDir, "GroundTruthTests");
                string expectedTestFilePath = Path.Combine(
                    groundTruthTestsDir,
                    "HashingLibraryTests.cs"
                );
                Assert.True(
                    File.Exists(expectedTestFilePath),
                    $"Expected test file not found: {expectedTestFilePath}"
                );

                string generatedTestContent = await File.ReadAllTextAsync(expectedTestFilePath);
                string expectedGeneratedTestCode =
                    @"using Xunit;
using System;
using System.Collections.Generic;
using System.IO;

namespace OutSystems.ExternalLibraries.Hashing.Tests
{
    public class HashingLibraryTests
    {
        private readonly HashingLibrary _library;

        public HashingLibraryTests()
        {
            _library = new HashingLibrary();
        }

        public static IEnumerable<object[]> TestData => new List<object[]>
        {
            new object[] { ""hello"", ""aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"" },
            new object[] { ""The quick brown fox jumps over the lazy dog"", ""2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"" },
            new object[] { ""12345"", ""8cb2237d0679ca88db6464eac60da96345513964"" },
            new object[] { ""Lorem ipsum dolor sit amet"", ""38f00f8738e241daea6f37f6f55ae8414d7b0219"" },
        };

        [Theory]
        [MemberData(nameof(TestData))]
        public void ComputeSHA1Hash_ValidInput_ReturnsExpectedOutput(string input, string expectedOutput)
        {
            // Act
            var result = _library.ComputeSHA1Hash(input);

            // Assert
            Assert.Equal(expectedOutput, result);
        }
    }
}";
                Assert.Equal(expectedGeneratedTestCode.Trim(), generatedTestContent.Trim());
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        [Fact]
        public async Task ShouldGenerateExpectedTestFile_ForBinaryReversal()
        {
            // Arrange
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string sourceFileName = "FileReverser.cs";
                string sourceFilePath = Path.Combine(projectDir, sourceFileName);
                await File.WriteAllTextAsync(
                    sourceFilePath,
                    BinaryReversalTestConstants.SourceCode
                );

                string gtTestDir = Path.Combine(tempDir, "GroundTruthTests");
                Directory.CreateDirectory(gtTestDir);
                string csprojPath = Path.Combine(gtTestDir, "GroundTruthTests.csproj");
                string csprojContent = WatermarkTestConstants.CsprojContent;
                await File.WriteAllTextAsync(csprojPath, csprojContent);

                string yamlFileName = "reversal.yaml";
                string yamlFilePath = Path.Combine(tempDir, yamlFileName);
                await File.WriteAllTextAsync(yamlFilePath, BinaryReversalTestConstants.YamlContent);

                string testDataDir = Path.Combine(tempDir, "test_data");
                Directory.CreateDirectory(testDataDir);
                string binaryFilePath = Path.Combine(testDataDir, "binary.bin");
                byte[] binaryBytes = [1, 2, 3, 4]; // Dummy data
                await File.WriteAllBytesAsync(binaryFilePath, binaryBytes);

                string binaryReversedFilePath = Path.Combine(testDataDir, "binary_reversed.bin");
                byte[] reversedBytes = [.. binaryBytes.Reverse()]; // Dummy data
                await File.WriteAllBytesAsync(binaryReversedFilePath, reversedBytes);

                string[] args = [sourceFilePath, yamlFilePath];
                // Act
                await Program.Main(args);

                // Assert
                string generatedTestFilePath = Path.Combine(gtTestDir, "FileReverserTests.cs");
                Assert.True(
                    File.Exists(generatedTestFilePath),
                    $"Expected test file not found: {generatedTestFilePath}"
                );

                string generatedTestContent = await File.ReadAllTextAsync(generatedTestFilePath);
                string expectedTestContent =
                    @"using Xunit;
using System;
using System.Collections.Generic;
using System.IO;

namespace MyCompany.ExternalLibraries.FileProcessing.Tests
{
    public class FileReverserTests
    {
        private readonly FileReverser _library;

        public FileReverserTests()
        {
            _library = new FileReverser();
        }

        public static IEnumerable<object[]> TestData => new List<object[]>
        {
            new object[] { File.ReadAllBytes(@""TestResources/binary.bin""), File.ReadAllBytes(@""TestResources/binary_reversed.bin"") },
        };

        [Theory]
        [MemberData(nameof(TestData))]
        public void ReverseFileBytes_ValidInput_ReturnsExpectedOutput(byte[] inputFile, byte[] expectedOutput)
        {
            // Act
            var result = _library.ReverseFileBytes(inputFile);

            // Assert
            Assert.Equal(expectedOutput, result);
        }
    }
}";
                Assert.Equal(expectedTestContent.Trim(), generatedTestContent.Trim());

                string testResourcesDir = Path.Combine(gtTestDir, "TestResources");
                Assert.True(Directory.Exists(testResourcesDir), "TestResources folder not found.");
                string[] resourceFiles = Directory.GetFiles(
                    testResourcesDir,
                    "*",
                    SearchOption.AllDirectories
                );
                Assert.Equal(2, resourceFiles.Length);
                string updatedCsprojContent = await File.ReadAllTextAsync(csprojPath);
                Assert.Contains(@"<Content Include=""TestResources\**\*""", updatedCsprojContent);
            }
            finally
            {
                // Cleanup temporary directory
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        [Fact]
        public async Task ShouldGenerateExpectedTestFile_WithParamMappingAndBinaryFiles_WhenYamlContainsBinaryPaths()
        {
            // Arrange
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string sourceFileName = "WatermarkLibrary.cs";
                string sourceFilePath = Path.Combine(projectDir, sourceFileName);
                string sourceCode = WatermarkTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string gtTestDir = Path.Combine(tempDir, "GroundTruthTests");
                Directory.CreateDirectory(gtTestDir);
                string csprojPath = Path.Combine(gtTestDir, "GroundTruthTests.csproj");
                string csprojContent = WatermarkTestConstants.CsprojContent;
                await File.WriteAllTextAsync(csprojPath, csprojContent);

                string yamlFileName = "watermark.yaml";
                string yamlFilePath = Path.Combine(tempDir, yamlFileName);
                await File.WriteAllTextAsync(yamlFilePath, WatermarkTestConstants.YamlContent);

                string testDataDir = Path.Combine(tempDir, "test_data");
                Directory.CreateDirectory(testDataDir);
                string lisbonSharpPath = Path.Combine(testDataDir, "lisbon_sharp.png");
                byte[] lisbonSharpBytes = [137, 80, 78, 71, 13, 10, 26, 10, 0x01, 0x02, 0x03, 0x04]; // Dummy data
                await File.WriteAllBytesAsync(lisbonSharpPath, lisbonSharpBytes);

                string fontPath = Path.Combine(testDataDir, "OpenSans-Regular.ttf");
                byte[] fontBytes = [137, 80, 78, 71, 13, 10, 26, 10, 0x0A, 0x0B, 0x0C, 0x0D]; // Dummy data
                await File.WriteAllBytesAsync(fontPath, fontBytes);

                string watermarkedPath = Path.Combine(testDataDir, "lisbon_sharp_watermarked.png");
                byte[] watermarkedBytes = [137, 80, 78, 71, 13, 10, 26, 10, 0xAA, 0xBB, 0xCC]; // Dummy data
                await File.WriteAllBytesAsync(watermarkedPath, watermarkedBytes);

                string paramMap =
                    "(WatermarkImage:imageInput=AddWatermark:imageData),"
                    + "(WatermarkImage:fontTTFInput=AddWatermark:fontData),"
                    + "(WatermarkImage:fontSizeInput=AddWatermark:fontSize),"
                    + "(WatermarkImage:displayTextInput=AddWatermark:text)";

                string[] args = [sourceFilePath, yamlFilePath, "--paramMap", paramMap];

                // Act
                await Program.Main(args);

                // Assert
                string generatedTestFilePath = Path.Combine(gtTestDir, "WatermarkLibraryTests.cs");
                Assert.True(
                    File.Exists(generatedTestFilePath),
                    $"Expected test file not found: {generatedTestFilePath}"
                );

                string generatedTestContent = await File.ReadAllTextAsync(generatedTestFilePath);
                string expectedTestContent =
                    @"using Xunit;
using System;
using System.Collections.Generic;
using System.IO;

namespace WatermarkLibrary.Tests
{
    public class WatermarkServiceTests
    {
        private readonly WatermarkService _library;

        public WatermarkServiceTests()
        {
            _library = new WatermarkService();
        }

        public static IEnumerable<object[]> TestData => new List<object[]>
        {
            new object[] { File.ReadAllBytes(@""TestResources/lisbon_sharp.png""), File.ReadAllBytes(@""TestResources/OpenSans-Regular.ttf""), 60d, ""DO NOT REPRODUCE"" },
        };

        [Theory]
        [MemberData(nameof(TestData))]
        public void AddWatermark_ValidInput_ReturnsValidPng(byte[] imageData, byte[] fontData, double fontSize, string text)
        {
            // Act
            var result = _library.AddWatermark(imageData, fontData, fontSize, text);

            // Assert
            // Validate that result is a valid PNG file by checking the PNG signature.
            byte[] pngSignature = new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 };
            Assert.True(result != null && result.Length >= pngSignature.Length, ""Output is not a valid PNG file."");
            for (int i = 0; i < pngSignature.Length; i++)
            {
                Assert.Equal(pngSignature[i], result[i]);
            }
        }
    }
}";
                Assert.Equal(expectedTestContent.Trim(), generatedTestContent.Trim());

                string testResourcesDir = Path.Combine(gtTestDir, "TestResources");
                Assert.True(Directory.Exists(testResourcesDir), "TestResources folder not found.");
                string[] resourceFiles = Directory.GetFiles(
                    testResourcesDir,
                    "*",
                    SearchOption.AllDirectories
                );
                Assert.Equal(3, resourceFiles.Length);
                string updatedCsprojContent = await File.ReadAllTextAsync(csprojPath);
                Assert.Contains(@"<Content Include=""TestResources\**\*""", updatedCsprojContent);
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        /// <summary>
        /// Verifies that using the <c>--report</c> flag prints the method and parameter mapping
        /// from the source file and YAML, without generating any tests.
        /// </summary>
        [Fact]
        public async Task ShouldPrintExpectedReportOutput_WhenReportModeIsUsed()
        {
            // Arrange
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string sourceFileName = "WatermarkLibrary.cs";
                string sourceFilePath = Path.Combine(projectDir, sourceFileName);
                string sourceCode = WatermarkTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string yamlFileName = "watermark.yml";
                string yamlFilePath = Path.Combine(tempDir, yamlFileName);
                string yamlContent = WatermarkTestConstants.YamlContent;
                await File.WriteAllTextAsync(yamlFilePath, yamlContent);

                string[] args = ["--report", sourceFilePath, yamlFilePath];

                // Act
                string output = await CaptureConsoleOutput(() => Program.Main(args));

                // Assert
                Assert.Contains("C# method name: AddWatermark", output);
                Assert.Contains("C# parameters:", output);
                Assert.Contains("- imageData (byte[])", output);
                Assert.Contains("- fontData (byte[])", output);
                Assert.Contains("- fontSize (double)", output);
                Assert.Contains("- text (string)", output);
                Assert.Contains("YAML method name: WatermarkImage", output);
                Assert.Contains("YAML parameters:", output);
                Assert.Contains("- imageInput", output);
                Assert.Contains("- fontTTFInput", output);
                Assert.Contains("- fontSizeInput", output);
                Assert.Contains("- displayTextInput", output);
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        /// <summary>
        /// Verifies that running with <c>--classname</c> prints the derived class name from the source.
        /// </summary>
        [Fact]
        public async Task ShouldPrintDerivedClassName_WhenClassNameModeIsUsed()
        {
            // Arrange: Create temporary project directory and source file for class name extraction.
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string sourceFilePath = Path.Combine(projectDir, "WatermarkLibrary.cs");
                string sourceCode = WatermarkTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string[] args = ["--classname", sourceFilePath];

                // Act: Capture the console output for class name mode
                string output = await CaptureConsoleOutput(() => Program.Main(args));

                // Assert: Verify that the derived class name is printed
                Assert.Contains("WatermarkService", output.Trim());
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        /// <summary>
        /// Verifies that running with <c>--map</c> prints the number of OSAction methods
        /// plus each method's parameter count.
        /// </summary>
        [Fact]
        public async Task ShouldPrintExpectedMapping_WhenMapModeIsUsed()
        {
            // Arrange
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);
                string sourceFilePath = Path.Combine(projectDir, "WatermarkLibrary.cs");
                string sourceCode = WatermarkTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string[] args = ["--map", sourceFilePath];

                // Act
                string output = await CaptureConsoleOutput(() => Program.Main(args));

                // Assert
                Assert.Equal("1(4)", output.Trim());
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }

        /// <summary>
        /// Verifies that running with <c>--addicon</c> updates the project file to embed the icon as a resource,
        /// and modifies the interface attribute to reference that icon resource name.
        /// </summary>
        [Fact]
        public async Task ShouldUpdateCsprojAndInterfaceWithIconResource_WhenAddIconModeIsUsed()
        {
            // Arrange: Create temporary project directory, csproj file, and source file for addicon mode
            string tempDir = CreateTemporaryDirectory();
            try
            {
                string projectDir = Path.Combine(tempDir, "TestProject");
                Directory.CreateDirectory(projectDir);

                string csprojPath = Path.Combine(projectDir, "GroundTruthTests.csproj");
                await File.WriteAllTextAsync(csprojPath, WatermarkTestConstants.CsprojContent);

                string sourceFileName = "WatermarkLibrary.cs";
                string sourceFilePath = Path.Combine(projectDir, sourceFileName);
                string sourceCode = WatermarkTestConstants.SourceCode;
                await File.WriteAllTextAsync(sourceFilePath, sourceCode);

                string[] args = ["--addicon", sourceFilePath, "test.png"];

                // Act: Capture the console output for addicon mode
                string output = await CaptureConsoleOutput(() => Program.Main(args));

                // Assert: Verify that the output messages indicate success
                Assert.Contains("Added test.png as EmbeddedResource to project file", output);
                Assert.Contains(
                    "Successfully updated interface and project file with icon resource: test.png",
                    output
                );

                // Assert: Verify that the csproj file has been updated correctly
                string updatedCsprojContent = await File.ReadAllTextAsync(csprojPath);
                Assert.Contains(
                    "\n  <ItemGroup>\n    <EmbeddedResource Include=\"test.png\" />\n  </ItemGroup>\n",
                    updatedCsprojContent
                );

                // Assert: Verify that the source file's OSInterface attribute is updated with the icon resource.
                string updatedSourceCode = await File.ReadAllTextAsync(sourceFilePath);
                Assert.DoesNotContain("[[", updatedSourceCode);
                Assert.DoesNotContain("]]", updatedSourceCode);
                string expectedIconResourceName = "WatermarkService.test.png";
                Assert.Contains(
                    $"IconResourceName = \"{expectedIconResourceName}\"",
                    updatedSourceCode
                );
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
        }
    }
}
