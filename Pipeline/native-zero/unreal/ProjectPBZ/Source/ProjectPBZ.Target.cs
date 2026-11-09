using UnrealBuildTool;
using System.Collections.Generic;

public class ProjectPBZTarget : TargetRules
{
	public ProjectPBZTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("ProjectPBZ");
	}
}
