using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace CCAGTestGenerator.Core.Services
{
    public static class CodeModificationService
    {
        /// <summary>
        /// Adds the specified icon to the <c>[OSInterface]</c> attribute of the found interface
        /// by updating or creating the <c>IconResourceName</c> property. If the
        /// <c>IconResourceName</c> is already specified, it is replaced.
        /// </summary>
        /// <param name="sourceCode">The original C# code.</param>
        /// <param name="iconFilename">The icon file to embed as resource.</param>
        /// <returns>The modified C# code including the <c>IconResourceName</c> property.</returns>
        /// <exception cref="InvalidOperationException">If no namespace or no interface with [OSInterface] is found.</exception>
        public static string AddIconToInterface(string sourceCode, string iconFilename)
        {
            var tree = CSharpSyntaxTree.ParseText(sourceCode);
            var root = tree.GetRoot();

            var interfaceDecl =
                root.DescendantNodes()
                    .OfType<InterfaceDeclarationSyntax>()
                    .FirstOrDefault(i => HasOSInterfaceAttribute(i))
                ?? throw new InvalidOperationException(
                    "No interface with [OSInterface] attribute found"
                );

            var interfaceName = interfaceDecl.Identifier.Text;
            var className = interfaceName.StartsWith('I') ? interfaceName[1..] : interfaceName;

            var iconResourceName = $"{className}.{iconFilename}";
            string newAttributeText;

            var attribute = interfaceDecl
                .AttributeLists.SelectMany(al => al.Attributes)
                .First(a => a.Name.ToString().Contains("OSInterface"));

            if (attribute.ArgumentList == null || !attribute.ArgumentList.Arguments.Any())
            {
                newAttributeText = $"[OSInterface(IconResourceName = \"{iconResourceName}\")]";
            }
            else
            {
                var args = attribute
                    .ArgumentList.Arguments.Where(arg =>
                        arg.NameEquals == null
                        || !arg.NameEquals.ToString().Contains("IconResourceName")
                    )
                    .Select(arg => arg.ToString())
                    .ToList();
                args.Add($"IconResourceName = \"{iconResourceName}\"");
                newAttributeText = $"[OSInterface({string.Join(", ", args)})]";
            }

            var attributeList =
                attribute.Parent as AttributeListSyntax
                ?? throw new InvalidOperationException(
                    "Attribute is not contained within an attribute list."
                );
            var oldAttributeListText = attributeList.ToString();
            return sourceCode.Replace(oldAttributeListText, newAttributeText);
        }

        /// <summary>
        /// Helper method to check if an interface declaration has <c>[OSInterface]</c>.
        /// </summary>
        /// <param name="interfaceDecl">The interface declaration node.</param>
        /// <returns>True if the interface has <c>[OSInterface]</c>; otherwise false.</returns>
        private static bool HasOSInterfaceAttribute(InterfaceDeclarationSyntax interfaceDecl)
        {
            return interfaceDecl
                .AttributeLists.SelectMany(al => al.Attributes)
                .Any(a => a.Name.ToString().Contains("OSInterface"));
        }
    }
}
