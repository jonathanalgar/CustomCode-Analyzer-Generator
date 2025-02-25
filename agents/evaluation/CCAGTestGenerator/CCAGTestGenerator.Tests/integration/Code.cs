namespace CCAGTestGenerator.Tests
{
    public static class HashingTestConstants
    {
        public const string SourceCode = """
using System;
using System.Security.Cryptography;
using System.Text;
using OutSystems.ExternalLibraries.SDK;

namespace OutSystems.ExternalLibraries.Hashing {

    [OSInterface(Name = "HashingLibrary")]
    public interface IHashingLibrary {

        [OSAction(Description = "Computes the SHA1 hash of the input string.")]
        string ComputeSHA1Hash([OSParameter(Description = "The input string to hash.")] string input);
    }

    public class HashingLibrary : IHashingLibrary {
        public string ComputeSHA1Hash(string input) {
            if (string.IsNullOrEmpty(input)) {
                throw new ArgumentException("Input cannot be null or empty.", nameof(input));
            }
            using (SHA1 sha1 = SHA1.Create()) {
                byte[] inputBytes = Encoding.UTF8.GetBytes(input);
                byte[] hashBytes = sha1.ComputeHash(inputBytes);
                StringBuilder sb = new StringBuilder();
                foreach (byte b in hashBytes) {
                    sb.Append(b.ToString("x2"));
                }
                return sb.ToString();
            }
        }
    }
}
""";

        public const string YamlContent = """
description: "Convert a string to its SHA1 hash value"
actions:
  GetSHA1Hash:
    params:
      - inputString
    testCases:
      - inputs:
          inputString: "hello"
        expected: "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
      - inputs:
          inputString: "The quick brown fox jumps over the lazy dog"
        expected: "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"
      - inputs:
          inputString: "12345"
        expected: "8cb2237d0679ca88db6464eac60da96345513964"
      - inputs:
          inputString: "Lorem ipsum dolor sit amet"
        expected: "38f00f8738e241daea6f37f6f55ae8414d7b0219"
""";
    }

    public static class BinaryReversalTestConstants
    {
        public const string SourceCode =
            @"using System.Linq;
using OutSystems.ExternalLibraries.SDK;

namespace MyCompany.ExternalLibraries.FileProcessing
{
    [OSInterface(Name = ""FileReverser"", Description = ""Provides functionality to reverse the bytes of a file"")]
    public interface IFileReverser
    {
        [OSAction(
            Description = ""Reverses the bytes of the input file"",
            ReturnName = ""ReversedFile"",
            ReturnDescription = ""Reversed byte array of the input file"",
            ReturnType = OSDataType.BinaryData
        )]
        byte[] ReverseFileBytes(
            [OSParameter(Description = ""Input byte array to reverse"", DataType = OSDataType.BinaryData)]
                byte[] inputFile
        );
    }

    public class FileReverser : IFileReverser
    {
        public byte[] ReverseFileBytes(byte[] inputFile)
        {
            ArgumentNullException.ThrowIfNull(inputFile);
            return inputFile.Reverse().ToArray();
        }
    }
}";
        public const string YamlContent =
            @"description: ""Take a byte file as input and return simply the reversed byte file as output""
actions:
  ReverseFileBytes:
    params:
      - inputFile
    testCases:
      - inputs:
          inputFile: ""path:./test_data/binary.bin""
        expected: ""path:./test_data/binary_reversed.bin""";

        public const string CsprojContent = """
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="CustomCode.Analyzer" Version="0.2.0">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="OutSystems.ExternalLibraries.SDK" Version="1.5.0" />
  </ItemGroup>

</Project>
""";
    }

    public static class WatermarkTestConstants
    {
        public const string SourceCode = """
using System;
using System.IO;
using SkiaSharp;
using OutSystems.ExternalLibraries.SDK;

namespace WatermarkLibrary
{
    [OSInterface(Name = "WatermarkLibrary", Description = "Provides functionality to add a watermark to an image.")]
    public interface IWatermarkService
    {
        [OSAction(Description = "Adds a watermark in the centre of an image.", ReturnName = "WatermarkedImage", ReturnType = OSDataType.BinaryData)]
        byte[] AddWatermark(
            [OSParameter(Description = "The original image in binary format.", DataType = OSDataType.BinaryData)] byte[] imageData,
            [OSParameter(Description = "The TTF font file in binary format.", DataType = OSDataType.BinaryData)] byte[] fontData,
            [OSParameter(Description = "The desired font size for the watermark.", DataType = OSDataType.Decimal)] double fontSize,
            [OSParameter(Description = "The watermark text to display in the centre of the image.", DataType = OSDataType.Text)] string text);
    }

    public class WatermarkService : IWatermarkService
    {
        public WatermarkService() { }

        public byte[] AddWatermark(byte[] imageData, byte[] fontData, double fontSize, string text)
        {
            if (imageData == null || imageData.Length == 0)
                throw new ArgumentException("Image data must be provided.", nameof(imageData));

            if (string.IsNullOrEmpty(text))
                throw new ArgumentException("Watermark text must be provided.", nameof(text));

            using (var inputStream = new MemoryStream(imageData))
            {
                SKBitmap bitmap = SKBitmap.Decode(inputStream);
                if (bitmap == null)
                    throw new ArgumentException("Invalid image data provided.");

                using (var canvas = new SKCanvas(bitmap))
                {
                    SKTypeface typeface = null;
                    if (fontData != null && fontData.Length > 0)
                    {
                        typeface = SKTypeface.FromData(SKData.CreateCopy(fontData));
                    }
                    if (typeface == null)
                    {
                        typeface = SKTypeface.Default;
                    }

                    using (var paint = new SKPaint())
                    {
                        paint.IsAntialias = true;
                        paint.Color = new SKColor(255, 255, 255, 128);
                        paint.TextSize = (float)fontSize;
                        paint.Typeface = typeface;

                        float textWidth = paint.MeasureText(text);
                        SKPaint.FontMetrics metrics;
                        paint.GetFontMetrics(out metrics);
                        float textHeight = metrics.Descent - metrics.Ascent;

                        float x = (bitmap.Width - textWidth) / 2;
                        float y = (bitmap.Height - textHeight) / 2 - metrics.Ascent;

                        canvas.DrawText(text, x, y, paint);
                    }
                }

                using (var image = SKImage.FromBitmap(bitmap))
                using (var data = image.Encode(SKEncodedImageFormat.Png, 100))
                {
                    return data.ToArray();
                }
            }
        }
    }
}
""";

        public const string YamlContent = """
description: "Take an image and return it with a watermark in the centre. Use the font ttf, font size and display text as inputs. White, 50% opacity. Use SkiaSharp package as it's MIT licensed"
actions:
  WatermarkImage:
    params:
      - imageInput
      - fontTTFInput
      - fontSizeInput
      - displayTextInput
    testCases:
      - inputs:
          imageInput: "path:./test_data/lisbon_sharp.png"
          fontTTFInput: "path:./test_data/OpenSans-Regular.ttf"
          fontSizeInput: 60
          displayTextInput: "DO NOT REPRODUCE"
        expected: "path:./test_data/lisbon_sharp_watermarked.png"
""";

        public const string CsprojContent = """
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="CustomCode.Analyzer" Version="0.2.0">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="OutSystems.ExternalLibraries.SDK" Version="1.5.0" />
  </ItemGroup>

</Project>
""";
    }
}
