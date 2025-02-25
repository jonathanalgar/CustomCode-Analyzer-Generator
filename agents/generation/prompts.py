from typing import NamedTuple

from langchain_core.prompts import ChatPromptTemplate


class SystemPrompt(NamedTuple):
    """Represents a prompt for the LLM."""

    name: str
    content: ChatPromptTemplate


SDK_SPECIFICATION = """\
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use this attribute to decorate a public .NET method you want to expose
    /// as an OutSystems Server Action. The method must be in the scope of a .NET
    /// interface decorated with OSInterface.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method)]
    public class OSActionAttribute : Attribute {{
        /// <summary>
        /// Defines the Description of the exposed OutSystems Server Action.
        /// </summary>
        public string Description {{ get; set; }}

        /// <summary>
        /// Defines the name of the embedded resource containing the icon for
        /// the exposed OutSystems Server Action.
        /// </summary>
        public string IconResourceName {{ get; set; }}

        /// <summary>
        /// If this .NET method has a returned value, this property defines the
        /// name for the exposed OutSystems Server Action Output Parameter. If
        /// not specified, the name is the name of the method.
        /// </summary>
        public string ReturnName {{ get; set; }}

        /// <summary>
        /// If this .NET method has a returned value, this property defines the
        /// description for the exposed OutSystems Server Action Output Parameter.
        /// </summary>
        public string ReturnDescription {{ get; set; }}

        /// <summary>
        /// If this .NET method has a returned value, this property defines the
        /// type for the exposed OutSystems Server Action Output Parameter. The
        /// specified type must be compatible with the .NET returned type. If
        /// not specified, the OutSystems type is inferred from the .NET type.
        /// </summary>
        public OSDataType ReturnType {{ get; set; }} = OSDataType.InferredFromDotNetType;

        /// <summary>
        /// Allows renaming the .NET method without breaking ODC apps consuming
        /// the exposed OutSystems Server Action. This property holds the
        /// original name of the method, so the key generated from the method
        /// name remains unchanged.
        /// </summary>
        public string OriginalName {{ get; set; }}
    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Represents an enumeration of the OutSystems data types.
    /// </summary>
    public enum OSDataType {{
        /// <summary>
        /// OutSystems data type is inferred from the .NET type.
        /// </summary>
        InferredFromDotNetType,

        /// <summary>
        /// Text type
        /// </summary>
        Text,

        /// <summary>
        /// Integer type
        /// </summary>
        Integer,

        /// <summary>
        /// Long Integer type
        /// </summary>
        LongInteger,

        /// <summary>
        /// Decimal type
        /// </summary>
        Decimal,

        /// <summary>
        /// Boolean type
        /// </summary>
        Boolean,

        /// <summary>
        /// DateTime type
        /// </summary>
        DateTime,

        /// <summary>
        /// Date type
        /// </summary>
        Date,

        /// <summary>
        /// Time type
        /// </summary>
        Time,

        /// <summary>
        /// Phone number type
        /// </summary>
        PhoneNumber,

        /// <summary>
        /// Email type
        /// </summary>
        Email,

        /// <summary>
        /// Binary type
        /// </summary>
        BinaryData,

        /// <summary>
        /// Currency type
        /// </summary>
        Currency
    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use to decorate a public property/field within a .NET struct decorated
    /// with OSStructure to specify that it shouldn't be exposed as an
    /// OutSystems Structure Attribute.
    /// </summary>
    public class OSIgnore : Attribute {{

    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use this attribute to decorate the entry point for the External Library.
    /// Only one .NET interface can be decorated with this attribute in the
    /// External Library. The interface must be implemented by a public class
    /// with a public parameterless constructor. All public methods within this
    /// .NET interface are exposed as OutSystems Server Actions.
    /// </summary>
    [AttributeUsage(AttributeTargets.Interface)]
    public class OSInterfaceAttribute : Attribute {{
        /// <summary>
        /// Defines the name of the External Library. If not specified, that
        /// name is the name of the .NET interface without the "I" prefix. This
        /// property allows users to set a custom name for the External Library.
        /// </summary>
        public string Name {{ get; set; }}

        /// <summary>
        /// Defines the description of the External Library.
        /// </summary>
        public string Description {{ get; set; }}

        /// <summary>
        /// Defines the name of the embedded resource containing the icon for
        /// the corresponding External Library.
        /// </summary>
        public string IconResourceName {{ get; set; }}

        /// <summary>
        /// Allows renaming the .NET interface without breaking ODC apps consuming it.
        /// This property holds the original name of the library (previous version
        /// namespace + previous version library name), so the key generated from the
        /// library name remains unchanged, and app references are not broken.
        /// </summary>
        public string OriginalName {{ get; set; }}
    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use this attribute to decorate a .NET method parameter you want to expose
    /// as an OutSystems Server Action Parameter. The method parameter must be
    /// in the scope of a .NET interface decorated with OSInterface.
    /// </summary>
    [AttributeUsage(AttributeTargets.Parameter)]
    public class OSParameterAttribute : Attribute {{
        /// <summary>
        /// Defines the Description of the exposed OutSystems Server Action Parameter.
        /// </summary>
        public string Description {{ get; set; }}

        /// <summary>
        /// Defines the type for the exposed OutSystems Server Action Parameter.
        /// The specified type must be compatible with the .NET parameter type.
        /// If not specified, the OutSystems type is inferred from the .NET type.
        /// </summary>
        public OSDataType DataType {{ get; set; }} = OSDataType.InferredFromDotNetType;

        /// <summary>
        /// Allows renaming the .NET method parameter without breaking ODC apps
        /// consuming it. This property holds the original name of the method
        /// parameter, so the key generated from the method parameter remains
        /// unchanged, and app references are not broken.
        /// </summary>
        public string OriginalName {{ get; set; }}
    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use this attribute to decorate a .NET struct you want to expose as an
    /// OutSystems Structure. All public fields and properties within the struct
    /// are exposed as OutSystems Structure Attributes.
    /// </summary>
    [AttributeUsage(AttributeTargets.Struct)]
    public class OSStructureAttribute : Attribute {{
        /// <summary>
        /// Defines the description of the exposed OutSystems Structure.
        /// </summary>
        public string Description {{ get; set; }}

        /// <summary>
        /// Allows renaming the .NET struct without breaking OutSystems apps
        /// consuming it. This property holds the original name of the struct,
        /// so the key generated from the struct name remains unchanged, and app
        /// references are not broken.
        /// </summary>
        public string OriginalName {{ get; set; }}
    }}
}}
namespace OutSystems.ExternalLibraries.SDK {{

    /// <summary>
    /// Use this attribute to decorate a .NET struct public property/field you
    /// want to expose as an OutSystems Structure Attribute. The property/field
    /// must be within the scope of a .NET struct decorated with
    /// OSStructureAttribute.
    /// </summary>
    public class OSStructureFieldAttribute : Attribute {{
        /// <summary>
        /// Defines the type of the exposed OutSystems Structure Attribute. The
        /// specified type must be compatible with the .NET parameter type. If
        /// not specified, the OutSystems type will be inferred from the .NET
        /// type.
        /// </summary>
        public string Description {{ get; set; }}

        /// <summary>
        /// Defines the maximum character length of the exposed OutSystems
        /// Structure Attribute. This only applies to Decimal and Text types.
        /// Default = 50.
        /// </summary>
        public int Length {{ get; set; }} = 50;

        /// <summary>
        /// Defines the number of decimal places of the exposed OutSystems
        /// Structure Attribute. This only applies to Decimal types. Default = 8.
        /// </summary>
        public int Decimals {{ get; set; }} = 8;

        /// <summary>
        /// Defines the type of the exposed OutSystems Structure Attribute. The
        /// specified type must be compatible with the .NET parameter type. If
        /// not specified, the OutSystems type will be inferred from the .NET
        /// type.
        /// </summary>
        public OSDataType DataType {{ get; set; }} = OSDataType.InferredFromDotNetType;

        /// <summary>
        /// Defines if the exposed OutSystems Structure Attribute requires a
        /// value to be set.
        /// </summary>
        public bool IsMandatory {{ get; set; }}

        /// <summary>
        /// Allows renaming the .NET struct property/field without breaking ODC
        /// apps consuming it. This property holds the original name of the
        /// struct property/field, so the key generated from the struct name
        /// remains unchanged, and app references are not broken.
        /// </summary>
        public string OriginalName {{ get; set; }}

        /// <summary>
        /// Defines the default value of the .NET struct property/field.
        /// </summary>
        public string DefaultValue {{ get; set; }}
    }}
}}
"""

BASE_URL = '$"https://{{Environment.GetEnvironmentVariable("SECURE_GATEWAY")}}:8080/"'


SYSTEM_PROMPT = f"""\
Generate C# code for an OutSystems external library to satisfy the user use case. * The implementation code and unit test code are separate assemblies.

## Implementation code

* Use the External Libraries SDK:
{SDK_SPECIFICATION}

* Use in-line comments to explain the code.
* Make use of packages from NuGet if needed.
* The implementation code should be contained in a namespace with a meaningful name.

## Unit test code

* Generate a simple XUnit test to verify the implementation.
* For network responses, use Moq to create appropriate mocks.
* When binary data (say an image or PDF) is needed as input, use a placeholder. Never try to generate a base64 or binary data string.
* The unit test code should be contained in a namespace with a meaningful name.

## Additional notes

You can connect your external library to private data and private services ("endpoints") that aren't accessible by the internet by using the Private Gateway feature.

You can use the connected endpoint(s) in your custom code using the hostname defined by the environment variable SECURE_GATEWAY. You use that hostname in conjunction with the configured ports.

For example, if you want to connect to a REST API endpoint on port 8080 you could use a string to define the base URL as {BASE_URL} if the endpoint is connected to cloud-connector over TLS/SSL or http if it's not.\
"""

EXAMPLE_1 = """\
Use case: take a string and return the sha1 hash
Some NuGet packages that may or may not be useful for the implementation code:

* Package: System.Security.Cryptography.Algorithms (v4.3.1)
  Description: Provides base types for cryptographic algorithms, including hashing, encryption, and signing operations.

Commonly Used Types:
System.Security.Cryptography.Aes
System.Security.Cryptography.RSA
System.Security.Cryptography.RSAParameters
System.Security.Cryptography.HMACSHA1
System.Security.Cryptography.SHA256
System.Security.Cryptography.SHA1
System.Security.Cryptography.SHA512
System.Security.Cryptography.SHA384
System.Security.Cryptography.HMACSHA256
System.Security.Cryptography.MD5
System.Security.Cryptography.HMACSHA384
System.Security.Cryptography.HMACSHA512

When using NuGet 3.x this package requires at least version 3.4.

* Package: Notus.Hash.SHA1 (v1.8.10)
  Description: This library contains the SHA1 Hash algorithm required for Notus.Network.

* Package: System.Data.HashFunction.CRC (v2.0.0)
  Description: Data.HashFunction implementation of the cyclic redundancy check (CRC) error-detecting code (http://en.wikipedia.org/wiki/Cyclic_redundancy_check).  Implementation is generalized to encompass all possible CRC parameters from 1 to 64 bits.\
"""

RESPONSE_1 = """\
{{
  "prefix": "This external library provides SHA1 haah functionality. The code defines an interface (ISha1Hasher) decorated with the OSInterface attribute and a method decorated with OSAction to compute the SHA1 hash from a given input string. The implementation uses .NET's built-in SHA1 cryptography provider to compute the hash and returns it as a hexadecimal string. The unit tests use xUnit to verify correct behavior including handling of null inputs.",
  "implementation_code": "using System.Security.Cryptography;
using System.Text;
using OutSystems.ExternalLibraries.SDK;

namespace MyCompany.ExternalLibraries.Security
{{
    // The OSInterface attribute exposes this interface as a external library
    [OSInterface(Name = "Sha1Hasher", Description = "Provides SHA1 hashing functionality")]
    public interface ISha1Hasher
    {{
        // The OSAction attribute exposes this method as a server action
        [OSAction(
            Description = "Computes the SHA1 hash of the input string",
            ReturnName = "SHA1Hash",
            ReturnDescription = "SHA1 hash of the input string",
            ReturnType = OSDataType.Text
        )]
        string ComputeSha1Hash(
            [OSParameter(Description = "Input string to hash", DataType = OSDataType.Text)]
                string input
        );
    }}

    // Implementation
    public class Sha1Hasher : ISha1Hasher
    {{
        // Computes the SHA1 hash for the input string
        public string ComputeSha1Hash(string input)
        {{
            ArgumentNullException.ThrowIfNull(input);
            // Convert the input string to a byte array using UTF8 encoding
            byte[] inputBytes = Encoding.UTF8.GetBytes(input);
            // Compute the SHA1 hash of the input bytes
            byte[] hashBytes = SHA1.HashData(inputBytes);
            // Convert the byte array to a hexadecimal string
            StringBuilder sb = new();
            foreach (byte b in hashBytes)
            {{
                sb.Append(b.ToString("x2"));
            }}
            return sb.ToString();
        }}
    }}
}}
",
  "unit_test_code": "using MyCompany.ExternalLibraries.Security;

namespace MyCompany.ExternalLibraries.Tests
{{
    public class Sha1HasherTests
    {{
        // Test to verify that the SHA1 hash is computed as expected
        [Fact]
        public void ComputeSha1Hash_ForHelloWorld_ReturnsExpectedHash()
        {{
            // Arrange: create an instance of the Sha1Hasher
            var hasher = new Sha1Hasher();
            string input = "hello world";
            string expectedHash = "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed";

            // Act: compute the hash
            string actualHash = hasher.ComputeSha1Hash(input);

            // Assert: verify that the computed hash matches the expected value
            Assert.Equal(expectedHash, actualHash);
        }}

        // Test to ensure that passing a null string throws an ArgumentNullException
        [Fact]
        public void ComputeSha1Hash_WithNullInput_ThrowsArgumentNullException()
        {{
            // Arrange: create an instance of the Sha1Hasher
            var hasher = new Sha1Hasher();

            // Act & Assert: null input should trigger an exception
            Assert.Throws<ArgumentNullException>(() => hasher.ComputeSha1Hash(null!));
        }}
    }}
}}
",
  "nuget_packages": "None"
}}\
"""


ZERO_SHOT_PROMPT = ChatPromptTemplate.from_messages(
    messages=[
        ("system", SYSTEM_PROMPT),
    ]
)

ONE_SHOT_PROMPT = ChatPromptTemplate.from_messages(
    messages=[
        ("system", SYSTEM_PROMPT),
        ("user", EXAMPLE_1),
        ("ai", RESPONSE_1),
    ]
)

PROMPTS: dict[str, ChatPromptTemplate] = {"ZERO_SHOT": ZERO_SHOT_PROMPT, "ONE_SHOT": ONE_SHOT_PROMPT}
