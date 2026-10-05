/-!
Small kernel-checked Boolean lemmas. This module intentionally needs only Lean
core. Mathlib is pinned by the surrounding Lake project for later extensions.
-/

namespace PNPResearch

/-- Pointwise conjunction is commutative for Boolean values. -/
theorem bool_and_comm (a b : Bool) : (a && b) = (b && a) := by
  cases a <;> cases b <;> rfl

/-- The same identity lifted to functions, with an arbitrary input type. -/
theorem function_and_comm {α : Type} (f g : α → Bool) :
    (fun x => f x && g x) = (fun x => g x && f x) := by
  funext x
  exact bool_and_comm (f x) (g x)

end PNPResearch
