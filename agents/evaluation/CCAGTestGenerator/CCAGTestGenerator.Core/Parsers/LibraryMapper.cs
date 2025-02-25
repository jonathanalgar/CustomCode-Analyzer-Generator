using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace CCAGTestGenerator.Core.Parsers
{
    public static class LibraryMapper
    {
        /// <summary>
        /// Scans the given source code to find the interface decorated with [OSInterface],
        /// counts all methods with [OSAction], and returns a string describing how many methods
        /// and how many parameters each method has.
        /// </summary>
        /// <param name="sourceCode">The entire source code of the library.</param>
        /// <returns>A string like "1(4)" meaning 1 method with 4 parameters, or "2(2, 3)" if multiple methods exist.</returns>
        public static string GetActionParamMap(string sourceCode)
        {
            var tree = CSharpSyntaxTree.ParseText(sourceCode);
            var root = tree.GetRoot();

            var interfaceDeclaration = root.DescendantNodes()
                .OfType<InterfaceDeclarationSyntax>()
                .FirstOrDefault(i => HasAttribute(i, "OSInterface"));
            if (interfaceDeclaration == null)
                return "0(0)";

            var methods = interfaceDeclaration
                .Members.OfType<MethodDeclarationSyntax>()
                .Where(m => HasAttribute(m, "OSAction"))
                .ToList();

            if (methods.Count == 0)
                return "0(0)";

            var paramCounts = methods
                .Select(m => m.ParameterList.Parameters.Count)
                .OrderBy(count => count)
                .ToList();

            return $"{methods.Count}({string.Join(", ", paramCounts)})";
        }

        private static bool HasAttribute(MemberDeclarationSyntax member, string attributeName)
        {
            return member
                .AttributeLists.SelectMany(al => al.Attributes)
                .Any(a => a.Name.ToString().Contains(attributeName));
        }
    }
}
