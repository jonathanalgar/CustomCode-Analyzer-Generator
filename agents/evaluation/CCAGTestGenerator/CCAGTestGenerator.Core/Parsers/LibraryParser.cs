using CCAGTestGenerator.Core.Utilities;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace CCAGTestGenerator.Core.Parsers
{
    /// <summary>
    /// Represents metadata about an ODC external library, extracted from a C# interface decorated with [OSInterface].
    /// </summary>
    public record ExternalLibraryInfo(
        string Namespace,
        string InterfaceName,
        string ClassName,
        string MethodName,
        IReadOnlyList<(string ParamName, string ParamType)> Parameters,
        string ReturnType
    );

    public static class LibraryParser
    {
        /// <summary>
        /// Parses a C# source file to locate the first interface with [OSInterface],
        /// extracts the first method with [OSAction], and returns an <see cref="ODCLibraryInfo"/>
        /// describing the discovered interface/class name, method name, parameters, and return type.
        /// </summary>
        /// <param name="sourceCode">The entire C# source code as a string.</param>
        /// <returns>An <see cref="ODCLibraryInfo"/> describing the discovered interface and method.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown if no interface with [OSInterface] or no method with [OSAction] is found.
        /// </exception>
        public static ExternalLibraryInfo ParseLibrary(string sourceCode)
        {
            var tree = CSharpSyntaxTree.ParseText(sourceCode);
            var root = tree.GetRoot();

            var interfaceDeclaration =
                root.DescendantNodes()
                    .OfType<InterfaceDeclarationSyntax>()
                    .FirstOrDefault(i => HasAttribute(i, "OSInterface"))
                ?? throw new InvalidOperationException(
                    "No interface with [OSInterface] attribute found"
                );

            var methodDeclaration =
                interfaceDeclaration
                    .Members.OfType<MethodDeclarationSyntax>()
                    .FirstOrDefault(m => HasAttribute(m, "OSAction"))
                ?? throw new InvalidOperationException(
                    $"No method with [OSAction] attribute found in interface {interfaceDeclaration.Identifier.Text}"
                );

            var parameters = new List<(string ParamName, string ParamType)>();
            foreach (var param in methodDeclaration.ParameterList.Parameters)
            {
                var paramName = param.Identifier.Text;
                var paramType =
                    param.Type?.ToString()
                    ?? throw new InvalidOperationException("Could not determine parameter type");
                if (!TypeMapper.TryGetTypeInfo(paramType, out _))
                    throw new InvalidOperationException($"Unsupported parameter type: {paramType}");
                parameters.Add((paramName, paramType));
            }

            var returnType = methodDeclaration.ReturnType.ToString();
            if (!TypeMapper.TryGetTypeInfo(returnType, out _))
                throw new InvalidOperationException($"Unsupported return type: {returnType}");

            var namespaceDecl =
                root.DescendantNodes().OfType<NamespaceDeclarationSyntax>().FirstOrDefault()
                ?? throw new InvalidOperationException("No namespace declaration found");

            var interfaceName = interfaceDeclaration.Identifier.Text;
            var className = interfaceName.StartsWith('I') ? interfaceName[1..] : interfaceName;

            return new ExternalLibraryInfo(
                Namespace: namespaceDecl.Name.ToString(),
                InterfaceName: interfaceName,
                ClassName: className,
                MethodName: methodDeclaration.Identifier.Text,
                Parameters: parameters,
                ReturnType: returnType
            );
        }

        /// <summary>
        /// Determines whether a given member has an attribute whose name contains the specified string.
        /// </summary>
        private static bool HasAttribute(MemberDeclarationSyntax member, string attributeName)
        {
            return member
                .AttributeLists.SelectMany(al => al.Attributes)
                .Any(a => a.Name.ToString().Contains(attributeName));
        }
    }
}
