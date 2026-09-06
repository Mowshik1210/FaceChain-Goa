# Standalone asset-path fix

- [x] Audit the entire project for obsolete hosted storage paths, vendor-specific storage wording, hosted image references, and favicon/logo dependencies.
- [x] Locate and recover the exact existing FaceChain Goa generated assets.
- [x] Copy recovered assets into `client/public/assets/` without redesigning the UI.
- [x] Replace every production asset reference with `/assets/...` paths, including CSS backgrounds.
- [x] Run `pnpm install`, `pnpm build`, and verify all assets exist in `dist/public/assets`.
- [x] Confirm zero obsolete hosted asset references and verify the production server serves the page and assets.
- [x] Report any unrecoverable exact asset clearly instead of substituting it.

## Verification notes

The recovered files were obtained from the existing generated assets in managed storage. Their artwork was preserved and re-encoded as optimized WebP copies for a standalone checkpoint-safe build; no replacement stock imagery was used. The optimized files keep the existing visual appearance while reducing the four asset files to well under 1 MB each.
