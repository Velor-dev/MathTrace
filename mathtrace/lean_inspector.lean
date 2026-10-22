/- Root-owned compiled-semantics/profile prototype. Not yet an acceptance gate.
   Elaborate this helper using only the verified official distribution; add
   inspected search roots inside main after trusted imports have completed.
   This is same-Lean evidence, not an independently implemented checker. -/
import Lean

open Lean

set_option maxRecDepth 100000

def object (fields : List (String × Json)) : Json := Json.mkObj fields

partial def exactName : Name → Json
  | .anonymous => Json.arr #[]
  | .str p s => Json.arr #[Json.str "str", exactName p, Json.str s]
  | .num p n => Json.arr #[Json.str "num", exactName p, toJson n]

def names (ns : List Name) : Json := Json.arr (ns.map exactName).toArray

partial def levelJson : Level → Json
  | .zero => Json.arr #[Json.str "zero"]
  | .succ u => Json.arr #[Json.str "succ", levelJson u]
  | .max u v => Json.arr #[Json.str "max", levelJson u, levelJson v]
  | .imax u v => Json.arr #[Json.str "imax", levelJson u, levelJson v]
  | .param n => Json.arr #[Json.str "param", exactName n]
  | .mvar n => Json.arr #[Json.str "mvar", exactName n.name]

def binder : BinderInfo → String
  | .default => "default"
  | .implicit => "implicit"
  | .strictImplicit => "strictImplicit"
  | .instImplicit => "instImplicit"

def hints : ReducibilityHints → Json
  | .opaque => Json.arr #[Json.str "opaque"]
  | .abbrev => Json.arr #[Json.str "abbrev"]
  | .regular n => Json.arr #[Json.str "regular", toJson n.toNat]

structure ExportState where
  index : Std.HashMap ExprStructEq Nat := {}
  normalized : Std.HashMap String Nat := {}
  expressions : Array Json := #[]

abbrev ExportM := StateT ExportState IO

partial def expression (e : Expr) : ExportM Nat := do
  if let .mdata _ body := e then return ← expression body
  -- Ordinary BEq Expr is alpha equivalence and ignores binder annotations.
  -- Structural equality deliberately preserves the exported syntax.
  if let some identifier := (← get).index[ExprStructEq.mk e]? then
    return identifier
  let node ← match e with
    | .bvar i => pure <| Json.arr #[Json.str "bvar", toJson i]
    | .fvar i => pure <| Json.arr #[Json.str "fvar", exactName i.name]
    | .mvar i => pure <| Json.arr #[Json.str "mvar", exactName i.name]
    | .sort u => pure <| Json.arr #[Json.str "sort", levelJson u]
    | .const n us => pure <| Json.arr #[Json.str "const", exactName n, Json.arr (us.map levelJson).toArray]
    | .app f a => do
      let f ← expression f
      let a ← expression a
      pure <| Json.arr #[Json.str "app", toJson f, toJson a]
    | .lam n t b i | .forallE n t b i => do
      let t ← expression t
      let b ← expression b
      let tag := if e.isLambda then "lam" else "forall"
      pure <| Json.arr #[Json.str tag, exactName n, toJson t, toJson b, Json.str (binder i)]
    | .letE n t v b nondep => do
      let t ← expression t
      let v ← expression v
      let b ← expression b
      pure <| Json.arr #[Json.str "let", exactName n, toJson t, toJson v, toJson b, toJson nondep]
    | .lit (.natVal n) => pure <| Json.arr #[Json.str "nat", toJson n]
    | .lit (.strVal s) => pure <| Json.arr #[Json.str "string", Json.str s]
    | .mdata _ _ => throw <| IO.userError "unreachable metadata export"
    | .proj n i b => do
      let b ← expression b
      pure <| Json.arr #[Json.str "proj", exactName n, toJson i, toJson b]
  let state ← get
  -- Intern the exported node too: parent syntax can differ solely through
  -- metadata in its descendants, which must not change normalized DAG identity.
  let key := node.compress
  if let some identifier := state.normalized[key]? then
    set {state with index := state.index.insert ⟨e⟩ identifier}
    return identifier
  if state.expressions.size >= 500000 then
    throw <| IO.userError "semantic expression budget exceeded; incomplete inspection is not evidence"
  let identifier := state.expressions.size
  set {state with index := state.index.insert ⟨e⟩ identifier,
                  normalized := state.normalized.insert key identifier,
                  expressions := state.expressions.push node}
  return identifier

def valueExpressions : ConstantInfo → List Expr
  | .defnInfo v => [v.value]
  | .thmInfo v => [v.value]
  | .opaqueInfo v => [v.value]
  | .recInfo v => v.rules.map (·.rhs)
  | _ => []

def relatedNames : ConstantInfo → List Name
  | .quotInfo _ => [``Eq, ``Quot, ``Quot.mk, ``Quot.lift, ``Quot.ind]
  | .inductInfo v => v.all ++ v.ctors ++ v.all.map (fun n => Name.str n "rec")
  | .ctorInfo v => [v.induct]
  | .recInfo v => v.all ++ v.rules.map (·.ctor)
  | .defnInfo v => v.all
  | .thmInfo v => v.all
  | .opaqueInfo v => v.all
  | _ => []

def expressionDependencies (e : Expr) : List Name := Id.run do
  let mut pending := [e]
  let mut visited : Std.HashSet ExprStructEq := {}
  let mut dependencies : NameSet := {}
  while !pending.isEmpty do
    let current := pending.head!
    pending := pending.tail!
    if visited.contains ⟨current⟩ then continue
    visited := visited.insert ⟨current⟩
    match current with
    | .const n _ => dependencies := dependencies.insert n
    | .proj n _ b =>
      dependencies := dependencies.insert n
      pending := b :: pending
    | .lam _ t b _ | .forallE _ t b _ => pending := t :: b :: pending
    | .letE _ t v b _ => pending := t :: v :: b :: pending
    | .app f a => pending := f :: a :: pending
    | .mdata _ b => pending := b :: pending
    | .lit (.natVal _) =>
      for n in [``Nat, ``Nat.zero, ``Nat.succ] do
        dependencies := dependencies.insert n
    | .lit (.strVal _) =>
      for n in [``String, ``String.ofList, ``Char, ``Char.ofNat,
                ``List, ``List.nil, ``List.cons, ``Nat, ``Nat.zero, ``Nat.succ] do
        dependencies := dependencies.insert n
    | _ => pure ()
  return dependencies.toArray.toList

def declaration (ci : ConstantInfo) (moduleName : Option Name) : ExportM Json := do
  let t ← expression ci.type
  let values ← (valueExpressions ci).mapM expression
  let detail := match ci with
    | .axiomInfo _ => object [("kind", "axiom")]
    | .defnInfo v => object [("kind", "definition"), ("safety", toJson (reprStr v.safety)),
        ("hints", hints v.hints), ("mutual", names v.all)]
    | .thmInfo v => object [("kind", "theorem"), ("mutual", names v.all)]
    | .opaqueInfo v => object [("kind", "opaque"), ("mutual", names v.all)]
    | .quotInfo v => object [("kind", "quotient"), ("quotient_kind", toJson (match v.kind with
        | .type => "type" | .ctor => "constructor" | .lift => "lift" | .ind => "induction"))]
    | .inductInfo v => object [("kind", "inductive"), ("parameters", toJson v.numParams),
        ("indices", toJson v.numIndices), ("mutual", names v.all), ("constructors", names v.ctors),
        ("nested", toJson v.numNested), ("recursive", toJson v.isRec), ("reflexive", toJson v.isReflexive)]
    | .ctorInfo v => object [("kind", "constructor"), ("inductive", exactName v.induct),
        ("index", toJson v.cidx), ("parameters", toJson v.numParams), ("fields", toJson v.numFields)]
    | .recInfo v => object [("kind", "recursor"), ("mutual", names v.all),
        ("parameters", toJson v.numParams), ("indices", toJson v.numIndices),
        ("motives", toJson v.numMotives), ("minors", toJson v.numMinors), ("k", toJson v.k),
        ("rules", toJson (v.rules.map fun r => object [("constructor", exactName r.ctor),
                                                        ("fields", toJson r.nfields)]))]
  return object [("name", exactName ci.name), ("display_name", toJson ci.name.toString),
    ("universe_parameters", Json.arr (ci.levelParams.map exactName).toArray),
    ("type", toJson t), ("values", toJson values), ("detail", detail),
    ("unsafe", toJson ci.isUnsafe), ("partial", toJson ci.isPartial),
    ("module", toJson (moduleName.map (·.toString)))]

def dependencies (ci : ConstantInfo) : List Name :=
  (ci.type :: valueExpressions ci).flatMap expressionDependencies ++ relatedNames ci

def closure (env : Environment) (initial : List Name) : IO (Array ConstantInfo) := do
  let mut pending := initial
  let mut seen : NameSet := {}
  let mut result := #[]
  while !pending.isEmpty do
    let name := pending.head!
    pending := pending.tail!
    if seen.contains name then continue
    if result.size >= 50000 then
      throw <| IO.userError "declaration budget exceeded; incomplete closure is not evidence"
    seen := seen.insert name
    let some ci := env.checked.get.find? name
      | throw <| IO.userError s!"missing actual semantic dependency: {name}"
    unless ci.name == name do
      throw <| IO.userError s!"constant lookup key/name mismatch: {name} / {ci.name}"
    result := result.push ci
    pending := dependencies ci ++ pending
  return result

def exportEntries (env : Environment) (entries : Array ConstantInfo)
    (origin : Option Environment := none) : IO Json := do
  let mut decls := #[]
  let mut axs : Array Json := #[]
  let mut state : ExportState := {}
  let origin := origin.getD env
  for ci in entries do
    let moduleName := (origin.getModuleIdxFor? ci.name).bind fun i => origin.header.moduleNames[i.toNat]?
    let (entry, next) ← (declaration ci moduleName).run state
    state := next
    decls := decls.push entry
    if ci.isAxiom then axs := axs.push (exactName ci.name)
  return object [("format", "lean-compiled-semantics-prototype-v1"),
    ("declarations", Json.arr decls), ("expressions", Json.arr state.expressions),
    ("axioms", Json.arr axs), ("metadata", "non-kernel expression metadata explicitly omitted"),
    ("complete", true), ("kernel", "same-Lean export; checking requires the enclosing verification profile")]

def inspect (env : Environment) (target : Name) (origin : Option Environment := none) : IO Json := do
  let entries ← closure env [target]
  let result ← exportEntries env entries origin
  let rootType := result.getObjValD "declarations" |>.getArrVal? 0 |>.toOption
    |>.bind (fun d => (d.getObjVal? "type").toOption) |>.getD Json.null
  return result.setObjVal! "target" (exactName target) |>.setObjVal! "root_type" rootType

def resolution (env : Environment) : IO Json := do
  let mut entries := #[]
  for name in env.header.moduleNames do
    let base ← findOLean name
    unless (← base.pathExists) do
      throw <| IO.userError s!"resolved module object is absent: {name}"
    let server := OLeanLevel.server.adjustFileName base
    let privatePart := OLeanLevel.private.adjustFileName base
    let ir := base.withExtension "ir"
    let serverPresent ← server.pathExists
    let privatePresent ← privatePart.pathExists
    let irPresent ← ir.pathExists
    entries := entries.push <| object [("module", exactName name),
      ("base", toJson base.toString),
      ("parts", object [("olean", toJson base.toString),
        ("server", if serverPresent then toJson server.toString else Json.null),
        ("private", if serverPresent && privatePresent then toJson privatePart.toString else Json.null),
        ("ir", if irPresent then toJson ir.toString else Json.null)])]
  return Json.arr entries

def primitiveProfile : String := "lean-4.30.0-reserved-primitives-v1"

def initExactSearchPath (paths : List System.FilePath := []) : IO Unit := do
  initSearchPath (← findSysroot) paths
  -- Lean splits LEAN_PATH="" into an empty current-directory entry. The
  -- evidence channel admits only explicit immutable roots and the sysroot.
  let current ← searchPathRef.get
  searchPathRef.set (current.filter fun path => !path.toString.isEmpty)

-- Reviewed against pinned type_checker.cpp, inductive.cpp, quot.cpp and Literal.type.
-- This is a finite primitive/dependency profile, not equality of all of Init/Std.
def primitiveSeeds : List Name :=
  [``Nat, ``Nat.zero, ``Nat.succ, ``Nat.add, ``Nat.sub, ``Nat.mul, ``Nat.pow,
   ``Nat.gcd, ``Nat.div, ``Nat.mod, ``Nat.beq, ``Nat.ble, ``Nat.land, ``Nat.lor,
   ``Nat.xor, ``Nat.shiftLeft, ``Nat.shiftRight, ``Bool, ``Bool.true, ``Bool.false,
   ``String, ``String.ofList, ``Char, ``Char.ofNat, ``List, ``List.nil, ``List.cons,
   ``Eq, ``Quot, ``Quot.mk, ``Quot.lift, ``Quot.ind, ``propext, ``Classical.choice,
   ``Quot.sound, `eagerReduce]

def canonicalDeclaration (ci : ConstantInfo) : IO Json := do
  let (entry, state) ← (declaration ci none).run {}
  return object [("declaration", entry), ("expressions", Json.arr state.expressions)]

def requireCorrespondence (expected actual : ConstantInfo) : IO Unit := do
  unless (← canonicalDeclaration expected) == (← canonicalDeclaration actual) do
    throw <| IO.userError s!"declaration correspondence differs: {expected.name}"

def requireSafe (ci : ConstantInfo) : IO Unit := do
  if ci.isUnsafe || ci.isPartial then
    throw <| IO.userError s!"unsafe/partial semantic dependency: {ci.name}"
  if ci.name == `Lean.reduceBool || ci.name == `Lean.reduceNat ||
     (dependencies ci).any (fun n => n == `Lean.reduceBool || n == `Lean.reduceNat) then
    throw <| IO.userError s!"native reduction requires a separate assurance profile: {ci.name}"

def verify (baseline imported : Environment) (target : Name) : IO Json := do
  let some (.thmInfo receiptValue) := imported.checked.get.find? target
    | throw <| IO.userError s!"exact receipt theorem is absent: {target}"
  unless receiptValue.name == target do
    throw <| IO.userError s!"receipt lookup key/name mismatch: {target} / {receiptValue.name}"
  let profile ← closure baseline primitiveSeeds
  let mut matched := 0
  for expected in profile do
    requireSafe expected
    if let some actual := imported.checked.get.find? expected.name then
      requireCorrespondence expected actual
      for name in dependencies expected do
        unless (imported.checked.get.find? name).isSome do
          throw <| IO.userError s!"missing primitive semantic dependency: {name}"
      matched := matched + 1
  let selected ← closure imported [target]
  for ci in selected do requireSafe ci
  -- Establish the official primitives first: stock replay's ordering omits
  -- implicit literal and projection edges. Missing ordinary dependencies fail closed.
  let profileMap := profile.foldl (fun m ci => m.insert ci.name ci) ({} : Std.HashMap Name ConstantInfo)
  let primitiveEnv ← (← mkEmptyEnvironment).replay profileMap
  for original in profile do
    let some actual := primitiveEnv.checked.get.find? original.name
      | throw <| IO.userError s!"replayed primitive is absent: {original.name}"
    requireCorrespondence original actual
  let selectedMap := selected.foldl (fun m ci =>
    if (primitiveEnv.checked.get.find? ci.name).isSome then m else m.insert ci.name ci)
    ({} : Std.HashMap Name ConstantInfo)
  let checked ← primitiveEnv.replay selectedMap
  let some (.thmInfo _) := checked.checked.get.find? target
    | throw <| IO.userError s!"exact replayed receipt theorem is absent: {target}"
  for original in selected do
    let some actual := checked.checked.get.find? original.name
      | throw <| IO.userError s!"replayed dependency is absent: {original.name}"
    requireCorrespondence original actual
  return object [("format", "lean-checked-target-profile-v2"),
    ("verification_mode", "checked-target"), ("lean_version", toJson Lean.versionString),
    ("primitive_profile", toJson primitiveProfile), ("primitive_reference_count", toJson profile.size),
    ("primitive_imported_matches", toJson matched), ("complete", true),
    ("assurance", "same-kernel theorem checking in pinned primitive context"),
    ("correspondence", "structural; expression metadata omitted; module origin is provenance only"),
    ("reference_profile", ← exportEntries baseline profile),
    ("semantics", ← inspect checked target (some imported))]

unsafe def verifyModule (moduleName symbol : String) (paths : List String)
    (consume : Json → IO Unit) (staged : Bool := false) : IO Unit := do
  initExactSearchPath
  withImportModules #[{module := `Init}] {} fun baseline => do
    -- Capture reference resolution before candidate roots can shadow any module.
    let referenceResolution ← resolution baseline
    let referencePaths ← searchPathRef.get
    initExactSearchPath (paths.map System.FilePath.mk)
    withImportModules #[{module := moduleName.toName}] {} fun imported => do
      let candidateResolution ← resolution imported
      let candidatePaths ← searchPathRef.get
      let report ← verify baseline imported symbol.toName
      -- Exported strings/names may refer to imported memory regions. Consume
      -- and serialize the complete report before withImportModules frees them.
      consume <| report.setObjVal! "resolution" <| object [
        ("reference", referenceResolution), ("candidate", candidateResolution),
        ("reference_search_roots", toJson (referencePaths.map (·.toString))),
        ("candidate_search_roots", toJson (candidatePaths.map (·.toString))),
        ("explicit_candidate_roots", toJson paths),
        ("channel", if staged then "resolution reconstructed under byte-verified staged roots; not an open-file trace"
                    else "resolution reconstructed under immutable roots; not an open-file trace"),
        ("import_mode", "withImportModules; private information; loadExts=false; no plugins")]

def expectRejection (action : IO Unit) : IO Unit := do
  let rejected ← try action; pure false catch _ => pure true
  unless rejected do throw <| IO.userError "comparison self-test unexpectedly accepted"

def comparisonSelfTest (baseline : Environment) : IO Json := do
  let some (.defnInfo addition) := baseline.checked.get.find? ``Nat.add
    | throw <| IO.userError "baseline addition is absent"
  let a := mkConst ``Nat
  let parent := mkApp a a
  let annotatedParent := mkApp a (mkMData {} a)
  let first := ConstantInfo.defnInfo {addition with value := mkApp annotatedParent parent}
  let second := ConstantInfo.defnInfo {addition with value := mkApp parent parent}
  requireCorrespondence first second
  expectRejection (requireCorrespondence (.defnInfo addition)
    (.defnInfo {addition with value := mkNatLit 0}))
  let some (.quotInfo quotient) := baseline.checked.get.find? ``Quot
    | throw <| IO.userError "baseline quotient is absent"
  expectRejection (requireCorrespondence (.quotInfo quotient)
    (.quotInfo {quotient with kind := .ctor}))
  expectRejection (requireSafe (.defnInfo {addition with value := mkConst `Lean.reduceNat}))
  return object [("metadata_normalization", true), ("definition_mismatch_rejected", true),
    ("quotient_kind_mismatch_rejected", true), ("native_reference_rejected", true),
    ("scope", "record comparison only; no altered declaration is replayed")]

unsafe def main (args : List String) : IO UInt32 := do
  unless Lean.versionString == "4.30.0" do
    throw <| IO.userError "this primitive profile supports only the pinned Lean 4.30.0 release"
  if let some value ← IO.getEnv "LEAN_PATH" then
    unless value.isEmpty do
      throw <| IO.userError "trusted helper loading requires an empty LEAN_PATH"
  match args with
  | "--verify-retained-output" :: output :: moduleName :: symbol :: paths =>
    verifyModule moduleName symbol paths (staged := true) fun report => do
      IO.FS.writeFile output report.compress
      IO.println <| (object [("format", "lean-checked-target-completion-v1"),
        ("complete", true), ("primitive_profile", toJson primitiveProfile),
        ("target", exactName symbol.toName)]).compress
    return 0
  | "--verify-retained" :: moduleName :: symbol :: paths =>
    verifyModule moduleName symbol paths fun report => do
      IO.FS.writeFile "/outputs/MathTraceSemantics.json" report.compress
      IO.println <| (object [("format", "lean-checked-target-completion-v1"),
        ("complete", true), ("primitive_profile", toJson primitiveProfile),
        ("target", exactName symbol.toName)]).compress
    return 0
  | ["--self-test"] =>
    initExactSearchPath
    withImportModules #[{module := `Init}] {} fun baseline => do
      IO.println (← comparisonSelfTest baseline).compress
    return 0
  | "--inspect" :: moduleName :: symbol :: paths =>
    initExactSearchPath (paths.map System.FilePath.mk)
    withImportModules #[{module := moduleName.toName}] {} fun env => do
      IO.println (← inspect env symbol.toName).compress
    return 0
  | moduleName :: symbol :: paths =>
    verifyModule moduleName symbol paths fun report => IO.println report.compress
    return 0
  | _ => throw <| IO.userError "usage: inspector MODULE EXACT_SYMBOL [INSPECTED_SEARCH_ROOT...]"
