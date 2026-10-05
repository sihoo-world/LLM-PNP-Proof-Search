namespace PNPResearchGenerated

theorem bool_and_comm (a b : Bool) : (a && b) = (b && a) := by
  cases a <;> cases b <;> rfl

end PNPResearchGenerated

#print axioms PNPResearchGenerated.bool_and_comm
