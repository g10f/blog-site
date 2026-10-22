const gulp = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const sourcemaps = require('gulp-sourcemaps');
const rename = require("gulp-rename");
const {parallel} = require('gulp');

const config = {
    srcCss: ['./apps/static/scss/main.scss'], buildCss: './apps/static/css'
};

// quietDeps: no deprecation warnings from Bootstrap's scss. silenceDeprecations 'import': Bootstrap 5
// only works with @import; sass is limited to ^1 in package.json, Dart Sass 3 removes @import.
function buildStyles() {
    return gulp.src(config.srcCss)
        .pipe(sourcemaps.init())
        .pipe(sass({loadPaths: ['node_modules'], quietDeps: true, silenceDeprecations: ['import']}).on('error', sass.logError))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(config.buildCss))
}

function buildMinStyles() {
    return gulp.src(config.srcCss)
        .pipe(sass({loadPaths: ['node_modules'], quietDeps: true, silenceDeprecations: ['import'], style: 'compressed'}).on('error', sass.logError))
        .pipe(rename({extname: '.min.css'}))
        .pipe(gulp.dest(config.buildCss))
}

function copyJavaScriptFiles() {
    // encoding: false keeps the files as buffers; gulp 5 otherwise reads them as
    // UTF-8 strings, which corrupts any non-text bytes (e.g. the font binaries below).
    return gulp.src([
        './node_modules/bootstrap/dist/js/bootstrap.bundle.min.js',
        './node_modules/bootstrap/dist/js/bootstrap.bundle.min.js.map',
        './node_modules/jquery/dist/jquery.min.js'], {encoding: false})
        .pipe(gulp.dest('./apps/static/js/vendor'))
}

function copyFontFiles() {
    // encoding: false: the woff/woff2 fonts are binary and must be copied as buffers,
    // not decoded as UTF-8 (see copyJavaScriptFiles).
    return gulp.src([
        './node_modules/bootstrap-icons/font/*.css',
        './node_modules/bootstrap-icons/font/**//fonts/*.*',
    ], {encoding: false}).pipe(gulp.dest('./apps/static/font'))
}

exports.default = parallel(buildStyles, buildMinStyles, copyJavaScriptFiles, copyFontFiles);
